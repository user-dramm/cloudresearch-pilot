// ============================================================================
//  PASTE THIS AS THE ENTIRE FILE.
//  In the Apps Script editor: click in the code area, select all (Ctrl+A / Cmd+A),
//  DELETE everything -- including Google's default `function myFunction() {}` --
//  then paste. If any part of this file ends up nested inside myFunction(), then
//  doGet, doPost and setup stop being global, Apps Script can no longer see them,
//  and the web app silently does nothing.
//  Check after pasting: `setup` should appear in the function dropdown at the top.
// ============================================================================

/**
 * Embrace CloudResearch pilot: response collector.
 *
 * Setup (5 minutes):
 *   1. Create a Google Sheet. Rename the first tab to "responses".
 *   2. Extensions -> Apps Script. Paste this file in, replacing Code.gs.
 *   3. In the editor, pick `setup` from the function dropdown and press Run. Authorise
 *      when Google asks. This creates both tabs with their headers and proves the script
 *      can write to your Sheet - do it BEFORE deploying, so an auth problem surfaces here
 *      rather than halfway through a paid session.
 *   4. Deploy -> New deployment -> type "Web app".
 *        Execute as:  Me
 *        Who has access:  Anyone            <- required; Connect workers are anonymous
 *   5. Copy the /exec URL into config.js as `endpoint`.
 *   6. Health check: open the /exec URL in a browser -> {"ok":true,...}. Then open the same
 *      URL in a PRIVATE window, logged out of Google. That is the check that matters:
 *      CloudResearch raters arrive anonymous, and your logged-in browser will succeed even
 *      when they cannot.
 *
 * Security note, stated plainly: this URL is public and lives in public
 * client-side code. TOKEN keeps drive-by bots out; it is not a secret. The real
 * protections are that this endpoint only ever APPENDS (it cannot read or edit
 * existing rows), and that junk rows are trivially deleted. Never put anything
 * confidential in the sheet.
 */

var TOKEN = "embr-pilot-2026-07";   // must match formToken in config.js
var SHEET = "responses";

/**
 * Leave empty if this script lives INSIDE your Sheet (you opened it via
 * Extensions -> Apps Script). Then it just uses that Sheet.
 *
 * If you created the script at script.google.com instead, it is "standalone" and has no
 * active spreadsheet - every write fails with a null error. Fix: paste your Sheet's ID
 * here. It is the long string in the Sheet's URL between /d/ and /edit:
 *   docs.google.com/spreadsheets/d/THIS_PART_HERE/edit
 */
var SHEET_ID = "";

/** Works whether the script is bound to the Sheet or standalone. */
function book_() {
  if (SHEET_ID) return SpreadsheetApp.openById(SHEET_ID);
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error(
    "No spreadsheet attached. This script is standalone - put your Sheet's ID in SHEET_ID " +
    "at the top of this file (the part of the Sheet URL between /d/ and /edit).");
  return ss;
}

/** Stable column order: this is what analysis.py expects from the CSV export.
 *
 *  REWRITTEN 2026-08-07 to match what the form actually sends. It had drifted badly:
 *  12 real answers had no column and were being written into the extra_json overflow,
 *  including BOTH clarity ratings, h2h_magnitude (which the "barely any difference"
 *  sensitivity check reads) and standby. Meanwhile 15 columns sat permanently blank,
 *  left over from an earlier question set (pacing, ai_read, per-section standby, the
 *  paste counters, h2h_confidence).
 *
 *  Nothing was ever LOST by that: analysis.py, decode_responses.py and make_report.py
 *  all read through a field() helper that unpacks extra_json. But a person opening the
 *  Sheet saw blank columns and a JSON blob where the answers should be, and that is the
 *  view used to spot-check participants and approve payment.
 *
 *  CHANGING THIS ARRAY IS SAFE ONLY WHILE THE SHEET HAS NO REAL ROWS. Rows are written
 *  as HEADERS.map(...), positionally, but the header row is only ever created once. So
 *  reordering or inserting mid-study writes new rows against the old header row and
 *  silently misaligns every column. To apply this: delete every row in the responses
 *  tab INCLUDING the header row, then submit once so the script recreates it.
 *
 *  `token` is deliberately absent. It is the same constant on every row, so it earns no
 *  column, and doPost drops it rather than letting it fall into the overflow.
 */
var HEADERS = [
  "row_id","ts_server","ts_client","study_tag","form_version","is_selftest",
  "participant_id","assignment_id","project_id",
  "pair_id","cc_code","video_source","slot1_key","slot2_key",

  /* Section 1: the four ratings, then the conditional narration follow-up, then the
     code word, then the playback telemetry. */
  "s1_overall","s1_audio","s1_visuals","s1_clarity","s1_audio_why","s1_codeword",
  "s1_watched_sec","s1_duration_sec","s1_watch_pct","s1_seek_fwd","s1_seek_back",
  "s1_load_errors","s1_max_rate","s1_rate_ms","s1_video_count","s1_cw_blocked",

  "s2_overall","s2_audio","s2_visuals","s2_clarity","s2_audio_why","s2_codeword",
  "s2_watched_sec","s2_duration_sec","s2_watch_pct","s2_seek_fwd","s2_seek_back",
  "s2_load_errors","s2_max_rate","s2_rate_ms","s2_video_count","s2_cw_blocked",

  /* The end block, in the order a rater answers it. */
  "h2h_choice","h2h_choice_slot","h2h_choice_key","h2h_magnitude","h2h_why",
  "standby","s1_comment","h2h_other",

  "assign_source","assign_nth","resumed_from_save",
  "total_ms","completion_code","user_agent","screen_w","screen_h","tz","referrer"
];

var ASSIGN_SHEET = "assignments";
var PENDING_MINUTES = 45;   // an assignment older than this is treated as abandoned

/**
 * Run this once from the editor before deploying. Creates the two tabs with their header
 * rows and triggers the authorisation prompt. Safe to run again - it won't duplicate
 * anything or touch existing rows.
 */
function setup() {
  var r = sheet_();
  var a = assignSheet_();
  var msg = "OK - " + book_().getName() + ": responses tab ready ("
          + (HEADERS.length + 1) + " columns), "
          + "assignments tab ready. Rows so far: "
          + Math.max(0, r.getLastRow() - 1) + " responses, "
          + Math.max(0, a.getLastRow() - 1) + " assignments.";
  Logger.log(msg);
  return msg;
}

function doGet(e) {
  var p = (e && e.parameter) || {};
  if (p.action === "assign") return assign_(p);
  return json({ ok: true, service: "embrace-pilot-collector", headers: HEADERS.length });
}

/**
 * Hands out the pair that currently has the FEWEST raters, instead of letting each
 * browser pick at random. Random assignment at n=35 across 5 pairs leaves some pair
 * with <=4 raters about 61% of the time, which is enough to sink the "new ahead in
 * 4 of 5 pairs" clause on noise alone.
 *
 * Counts completed responses, plus assignments from the last PENDING_MINUTES that
 * haven't completed yet (so someone who opens the link and wanders off stops holding
 * a slot). Returns `nth` as well, which the form uses to alternate A/B order - that
 * keeps video order near-perfectly balanced within each pair too.
 */
function assign_(p) {
  if (p.token !== TOKEN) return json({ ok: false, error: "bad token" });
  var ids = String(p.pairs || "").split(",").map(function (x) { return x.trim(); }).filter(String);
  if (!ids.length) return json({ ok: false, error: "no pairs supplied" });
  var pid = String(p.pid || "");

  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);

    var counts = {};
    ids.forEach(function (id) { counts[id] = 0; });

    // --- completed responses ---
    var done = {};                                  // pid -> true
    var rs = book_().getSheetByName(SHEET);
    if (rs && rs.getLastRow() > 1) {
      var rv = rs.getDataRange().getValues();
      var head = rv[0];
      var iPid = head.indexOf("participant_id"), iPair = head.indexOf("pair_id");
      if (iPid < 0 || iPair < 0) return json({ ok: false, error: "responses tab headers missing - run setup()" });
      for (var i = 1; i < rv.length; i++) {
        var rp = String(rv[i][iPair]);
        done[String(rv[i][iPid])] = true;
        if (counts.hasOwnProperty(rp)) counts[rp]++;
      }
    }

    // --- assignments: this participant's own, and live pending ones ---
    var ash = assignSheet_();
    var av = ash.getLastRow() > 1 ? ash.getDataRange().getValues() : [[]];
    var cutoff = Date.now() - PENDING_MINUTES * 60 * 1000;
    var mine = null, mineNth = 0;
    for (var j = 1; j < av.length; j++) {
      var apid = String(av[j][0]), apair = String(av[j][1]), ats = Date.parse(av[j][2]);
      if (apid === pid && mine === null) { mine = apair; mineNth = Number(av[j][3]) || 0; }
      if (apid !== pid && !done[apid] && ats > cutoff && counts.hasOwnProperty(apair)) counts[apair]++;
    }

    // A refresh must not reroll into a different pair.
    if (mine && counts.hasOwnProperty(mine)) {
      return json({ ok: true, pair: mine, nth: mineNth, repeat: true });
    }

    var best = ids[0];
    ids.forEach(function (id) { if (counts[id] < counts[best]) best = id; });
    var nth = counts[best];
    ash.appendRow([pid, best, new Date().toISOString(), nth]);
    return json({ ok: true, pair: best, nth: nth, counts: counts });

  } catch (err) {
    return json({ ok: false, error: String(err) });
  } finally {
    try { lock.releaseLock(); } catch (_) {}
  }
}

function assignSheet_() {
  var ss = book_();
  var sh = ss.getSheetByName(ASSIGN_SHEET) || ss.insertSheet(ASSIGN_SHEET);
  if (sh.getLastRow() === 0) {
    sh.appendRow(["participant_id", "pair_id", "assigned_at", "nth_in_pair"]);
    sh.setFrozenRows(1);
  }
  return sh;
}

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    lock.waitLock(20000);

    var d = JSON.parse(e.postData.contents);
    if (d.token !== TOKEN) return json({ ok: false, error: "bad token" });
    delete d.token;

    var sh = sheet_();
    var rowId = "R" + Date.now() + "-" + Math.floor(Math.random() * 900 + 100);
    d.row_id = rowId;
    d.ts_server = new Date().toISOString();

    var row = HEADERS.map(function (h) { return h in d ? d[h] : ""; });

    // Anything the form sent that HEADERS doesn't know about goes in an overflow
    // column, so a field added to the form is never silently dropped.
    var extra = {};
    Object.keys(d).forEach(function (k) {
      // `token` is the same constant on every row and has no column by design, so it
      // would otherwise be the only thing in extra_json on a normal submission.
      if (k !== "token" && HEADERS.indexOf(k) === -1) extra[k] = d[k];
    });
    row.push(Object.keys(extra).length ? JSON.stringify(extra) : "");

    sh.appendRow(row);
    return json({ ok: true, rowId: rowId });

  } catch (err) {
    return json({ ok: false, error: String(err) });
  } finally {
    try { lock.releaseLock(); } catch (_) {}
  }
}

function sheet_() {
  var ss = book_();
  var sh = ss.getSheetByName(SHEET) || ss.insertSheet(SHEET);
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEADERS.concat(["extra_json"]));
    sh.setFrozenRows(1);
  }
  return sh;
}

function json(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}
