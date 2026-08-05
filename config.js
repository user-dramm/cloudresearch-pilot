/* ============================================================================
   STUDY CONFIG — Embrace Pilot 2026-07, blind old-vs-new, 5 CC course pairs
   ----------------------------------------------------------------------------
   This file is PUBLIC (it ships to the participant's browser). Nothing in here
   may reveal which version is old and which is new. Version keys are opaque on
   purpose; the old/new mapping lives in decode_key.json, which is gitignored
   and used only by analysis.py.
   ============================================================================ */

window.STUDY_CONFIG = {

  studyTag: "pilot-2026-07",

  /* "file" = self-hosted MP4s via a plain <video> tag (recommended: tighter
     blinding, real seek-blocking, no third-party dependency).
     "youtube" = unlisted YouTube embeds via the IFrame API (zero infrastructure,
     adaptive bitrate on bad connections). Switching is one word; the gate,
     the data schema, and the analysis are identical either way.
     Currently YOUTUBE: see the upload discipline checklist in README, which is
     what closes the blinding gap this backend leaves open. */
  videoSource: "youtube",

  /* file mode only: rewind any attempt to scrub past the furthest point
     genuinely watched. YouTube mode can't do this - it can only decline to
     credit the skipped time. */
  blockSeeking: true,

  /* Paste the Apps Script web-app /exec URL here after deploying.
     This URL is public by design. The endpoint is append-only; see Code.gs. */
  endpoint: "https://script.google.com/macros/s/AKfycbzlJjh67g33lmEEJslD9JhMhKQj3lulof4UAXlZ12auC4_7D7DX4DEQskGpdES2n3Zx/exec",

  /* Weak bot filter, not security. Must match TOKEN in Code.gs. */
  formToken: "embr-pilot-2026-07",

  /* Shown once a response is confirmed saved. Must match the fixed code you set
     in Connect. Connect disallows 0, 1, I and O in fixed codes - this one is clean. */
  completionCode: "EMBR7K2QX4",

  /* Paste the Redirect URL from the end of Connect's Create-a-Study wizard.
     Connect calls this the most reliable completion method: the participant is
     sent back automatically instead of having to copy the code across. Leave it
     empty to fall back to code-only. */
  redirectUrl: "",

  /* Fraction of each clip that must actually play before questions unlock.
     Only genuine playback counts — seeking forward earns no credit. */
  watchGate: 0.90,

  /* Minimum characters for the free-text answers (quality gate). */
  minCommentChars: 60,
  minWhyChars: 80,

  /* ------------------------------------------------------------------------
     PAIRS
     - enabled:false pairs are auto-excluded from random assignment, so an
       unfinished pair can sit here harmlessly until its clips exist.
     - versions: exactly two entries. The keys are opaque labels you invent;
       do not name them old/new. Record the true mapping in decode_key.json.
     - yt:  the unlisted YouTube video ID (the part after v=)  [youtube mode]
     - src: a direct https URL to the .mp4                     [file mode]
       Only the one matching videoSource has to be filled in.
     ------------------------------------------------------------------------ */
  pairs: [
    {
      id: "P1", cc: "EMBR-CC-00051", enabled: false,
      versions: [
        { key: "k3ta", yt: "", src: "" },
        { key: "k9vm", yt: "", src: "" }
      ]
    },
    {
      id: "P2", cc: "EMBR-CC-00158", enabled: true,
      versions: [
        { key: "k5qd", yt: "REPLACE_YT_ID", src: "https://clips.example.com/k5qd.mp4" },
        { key: "k2wj", yt: "REPLACE_YT_ID", src: "https://clips.example.com/k2wj.mp4" }
      ]
    },
    {
      id: "P3", cc: "EMBR-CC-00162", enabled: true,
      versions: [
        { key: "k8rn", yt: "REPLACE_YT_ID", src: "https://clips.example.com/k8rn.mp4" },
        { key: "k4zf", yt: "REPLACE_YT_ID", src: "https://clips.example.com/k4zf.mp4" }
      ]
    },
    {
      id: "P4", cc: "EMBR-CC-00175", enabled: false,
      versions: [
        { key: "k6hb", yt: "", src: "" },
        { key: "k1ps", yt: "", src: "" }
      ]
    },
    {
      id: "P5", cc: "EMBR-CC-00254", enabled: true,
      versions: [
        { key: "k7cy", yt: "REPLACE_YT_ID", src: "https://clips.example.com/k7cy.mp4" },
        { key: "k0lg", yt: "REPLACE_YT_ID", src: "https://clips.example.com/k0lg.mp4" }
      ]
    }
  ]
};
