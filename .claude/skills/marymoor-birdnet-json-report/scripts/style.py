"""Page styling mirroring the Eastside Audubon eBird Weekly newsletter."""

CSS = r"""
:root{
  --navy:#1a375f; --blue:#0068a6; --sky:#0fa7e3; --tile-label:#b3d9f2;
  --bg:#ffffff; --surface:#ffffff; --surface-alt:#f8f9fa; --border:#e0e0e0;
  --text:#1f2933; --muted:#5f5f5f; --faint:#999999; --heading:#1a375f;
  --link:#0068a6; --focus:rgba(0,104,166,.2); --hover:#f0f7ff;
  --high:#1b7f3b; --high-bg:#e3f4e8; --med:#8a5a00; --med-bg:#fff3d6;
  --low:#8a8a8a; --low-bg:#f0f0f0; --night:#2c2a5a; --night-bg:#ecebfa;
  --owl:#7a4b12; --owl-bg:#fbefdc; --review:#a3271f; --review-bg:#fde7e5;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --navy:#10233d; --blue:#0b4f7d; --tile-label:#9cc8e8;
    --bg:#0f1720; --surface:#16202b; --surface-alt:#1b2733; --border:#2a3746;
    --text:#e3e8ee; --muted:#a7b3c0; --faint:#7e8b98; --heading:#cfe2f7;
    --link:#6cc2f5; --hover:#1d2c3b;
    --high:#7fd69a; --high-bg:#173523; --med:#f2c46b; --med-bg:#3a2d10;
    --low:#a5adb6; --low-bg:#262f39; --night:#c9c6ff; --night-bg:#26244a;
    --owl:#f2c58a; --owl-bg:#3a2a14; --review:#ff9a90; --review-bg:#40201d;
  }
}
:root[data-theme="dark"]{
  --navy:#10233d; --blue:#0b4f7d; --tile-label:#9cc8e8;
  --bg:#0f1720; --surface:#16202b; --surface-alt:#1b2733; --border:#2a3746;
  --text:#e3e8ee; --muted:#a7b3c0; --faint:#7e8b98; --heading:#cfe2f7;
  --link:#6cc2f5; --hover:#1d2c3b;
  --high:#7fd69a; --high-bg:#173523; --med:#f2c46b; --med-bg:#3a2d10;
  --low:#a5adb6; --low-bg:#262f39; --night:#c9c6ff; --night-bg:#26244a;
  --owl:#f2c58a; --owl-bg:#3a2a14; --review:#ff9a90; --review-bg:#40201d;
}
*{box-sizing:border-box;font-family:'Source Sans 3',system-ui,sans-serif}
body{margin:0;background:var(--bg);color:var(--text);line-height:1.45}
a{color:var(--link);text-decoration:none} a:hover{text-decoration:underline}
.mast{background:var(--navy);color:#fff;padding:36px 40px 32px}
.mast-inner{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}
.mark{width:96px;height:96px;flex:none}
.logo{height:110px;width:auto;flex:none}
.mast-text{flex:1;min-width:240px}
.mast h1{margin:0;font-size:36px;font-weight:700;line-height:1.15}
.kicker{font-size:15px;color:rgba(255,255,255,.7);letter-spacing:1.5px;text-transform:uppercase}
.mast p{font-size:14px;font-weight:300;color:rgba(255,255,255,.6);margin:10px 0 0;max-width:760px}
.mast p a{color:var(--sky)}
.mast-date{text-align:right;font-size:15px;color:rgba(255,255,255,.85);white-space:nowrap;padding-top:4px}
.stats{background:var(--blue);padding:22px 40px;display:grid;grid-template-columns:repeat(5,1fr);gap:8px}
.stat{text-align:center;color:#fff}
.stat b{display:block;font-size:36px;font-weight:700;line-height:1.1}
.stat span{font-size:12px;color:var(--tile-label);letter-spacing:1px;text-transform:uppercase}
.section{padding:24px 40px 8px}
.section h2{margin:0;font-size:24px;font-weight:600;color:var(--heading)}
.section .lede{font-size:15px;font-weight:300;color:var(--muted);margin:6px 0 16px}
.body{padding:0 40px}
.intro{font-size:16px;color:var(--text);max-width:820px}
details{border:1px solid var(--border);border-radius:8px;margin-bottom:8px;overflow:hidden;background:var(--surface)}
summary{padding:16px 20px;cursor:pointer;display:flex;align-items:center;gap:12px;list-style:none;flex-wrap:wrap}
summary::-webkit-details-marker{display:none}
summary::before{content:"\25B6";font-size:11px;color:var(--faint);transition:transform .2s}
details[open]>summary::before{transform:rotate(90deg)}
summary:hover{background:var(--hover)}
.hs-name{font-size:18px;font-weight:600;color:var(--heading)}
.hs-stats{font-size:14px;font-weight:300;color:var(--muted);margin-left:auto}
.wrap{padding:4px 20px 16px;border-top:1px solid var(--border);overflow-x:auto}
table.sp{width:100%;border-collapse:collapse;font-size:14px}
table.sp thead td{font-weight:600;color:var(--heading);padding:8px;border-bottom:1px solid var(--border);font-size:13px;letter-spacing:.5px;white-space:nowrap}
table.sp tbody td{padding:6px 8px;font-weight:400;vertical-align:middle}
table.sp tbody tr:nth-child(even) td{background:var(--surface-alt)}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.rank{color:var(--faint);width:36px;text-align:right}
.com{color:var(--heading);font-weight:600}
.sci{font-style:italic;color:var(--muted)}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;white-space:nowrap}
.p-high{color:var(--high);background:var(--high-bg)}
.p-med{color:var(--med);background:var(--med-bg)}
.p-low{color:var(--low);background:var(--low-bg)}
.p-night{color:var(--night);background:var(--night-bg)}
.p-day{color:var(--muted);background:var(--surface-alt);border:1px solid var(--border)}
.p-owl{color:var(--owl);background:var(--owl-bg)}
.p-review{color:var(--review);background:var(--review-bg)}
.conf{font-weight:700;font-variant-numeric:tabular-nums}
audio{height:32px;width:220px;max-width:100%;vertical-align:middle}
.clipref{font-size:12px;color:var(--faint);word-break:break-all}
.sub{padding:0 0 4px;font-size:13px;color:var(--muted)}
.inner{margin:8px 0 0 0}
.inner details{margin:6px 0}
.inner summary{padding:8px 12px;font-size:14px}
.legend{display:flex;gap:10px;flex-wrap:wrap;font-size:13px;color:var(--muted);margin:0 0 14px}
.note{font-size:14px;color:var(--muted);border-left:3px solid var(--blue);padding:6px 12px;margin:10px 0 18px;background:var(--surface-alt)}
footer{margin-top:32px;background:var(--navy);color:rgba(255,255,255,.75);padding:24px 40px;font-size:13px;font-weight:300}
footer a{color:var(--sky)}
@media (max-width:720px){
  .mast{padding:24px 16px}.mast h1{font-size:28px}.mast-date{text-align:left;white-space:normal}
  .mark{width:64px;height:64px}.logo{height:72px}
  .stats{grid-template-columns:repeat(2,1fr);padding:16px}.stat b{font-size:28px}
  .section{padding:20px 16px 6px}.body{padding:0 16px}footer{padding:20px 16px}
  summary{padding:12px 14px}.hs-stats{margin-left:0;width:100%}
  .wrap{padding:4px 10px 12px}
  table.sp .hide-sm{display:none}
  audio{width:170px}
}
"""

OWL_SVG = """<svg class="mark" viewBox="0 0 96 96" role="img" aria-label="Owl">
<circle cx="48" cy="48" r="46" fill="none" stroke="rgba(255,255,255,.35)" stroke-width="2"/>
<path d="M26 30 L34 40 M70 30 L62 40" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
<path d="M30 40 Q48 26 66 40 L66 62 Q48 82 30 62 Z" fill="rgba(255,255,255,.12)" stroke="#fff" stroke-width="2.5"/>
<circle cx="40" cy="48" r="8" fill="none" stroke="#fff" stroke-width="2.5"/><circle cx="40" cy="48" r="3" fill="#0fa7e3"/>
<circle cx="56" cy="48" r="8" fill="none" stroke="#fff" stroke-width="2.5"/><circle cx="56" cy="48" r="3" fill="#0fa7e3"/>
<path d="M45 56 L48 62 L51 56 Z" fill="#fff"/>
</svg>"""
