TEMPLATE = r'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>__TITLE__</title>
<meta name="theme-color" content="#160A26">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect x='4' y='10' width='56' height='40' rx='20' fill='%232F4BFF'/><path d='M14 44 L8 58 L26 48Z' fill='%232F4BFF'/></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anybody:wdth,wght@50..150,400..900&family=Onest:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/modern-screenshot@4.4.39/dist/index.js"></script>
<style>
:root{
  --ink:#241038; --night:#160A26; --lilac:#EEE8FF; --lav:#DCD3F5;
  --cobalt:#2F4BFF; --pink:#FF5FA2; --white:#FFFFFF;
  --cw:min(100vw, calc(92dvh * 9 / 16));
  --ch:calc(var(--cw) * 16 / 9);
  --display:'Anybody',system-ui,sans-serif;
  --body:'Onest',system-ui,sans-serif;
  --ease:cubic-bezier(.2,.8,.2,1);
  --spring:cubic-bezier(.3,1.4,.5,1);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:var(--night);color:var(--white);font-family:var(--body);-webkit-font-smoothing:antialiased;overflow:hidden;user-select:none;-webkit-user-select:none;-webkit-tap-highlight-color:transparent;touch-action:pan-y;transition:background .6s var(--ease)}
button{font:inherit;color:inherit;cursor:pointer}
:focus-visible{outline:2px solid currentColor;outline-offset:3px}

/* themes */
.t-cobalt{--bg:var(--cobalt);--fg:var(--white);--soft:rgba(255,255,255,.14);--tint:#9FB0FF}
.t-lilac{--bg:var(--lilac);--fg:var(--ink);--soft:rgba(36,16,56,.08);--tint:var(--cobalt)}
.t-white{--bg:var(--white);--fg:var(--ink);--soft:rgba(36,16,56,.07);--tint:var(--cobalt)}
.t-ink{--bg:var(--ink);--fg:var(--lilac);--soft:rgba(238,232,255,.1);--tint:var(--pink)}
.t-night{--bg:var(--night);--fg:var(--lilac);--soft:rgba(238,232,255,.09);--tint:var(--pink)}
.t-pink{--bg:var(--pink);--fg:var(--ink);--soft:rgba(36,16,56,.1);--tint:var(--white)}
.t-lav{--bg:var(--lav);--fg:var(--ink);--soft:rgba(36,16,56,.08);--tint:var(--cobalt)}
.t-stage{--bg:var(--cobalt);--fg:var(--white);--soft:rgba(255,255,255,.14);--tint:#9FB0FF}

/* deck */
.deck{position:fixed;inset:0}
.slide{position:absolute;inset:0;display:grid;place-items:center;opacity:0;visibility:hidden;transform:translateX(5%) scale(.97);transition:opacity .45s var(--ease),transform .55s var(--ease),visibility 0s .55s}
.slide.past{transform:translateX(-5%) scale(.97)}
.slide.on{opacity:1;visibility:visible;transform:none;transition:opacity .45s var(--ease),transform .55s var(--ease),visibility 0s}
.card{position:relative;width:var(--cw);height:var(--ch);border-radius:calc(var(--cw) * .075);background:var(--bg);color:var(--fg);font-size:calc(var(--cw) / 22);padding:5.2em 1.6em 1.3em;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 30px 80px -30px rgba(0,0,0,.5)}
.body{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:.2em;min-height:0}
.mark{display:flex;justify-content:space-between;font-family:var(--display);font-weight:700;font-stretch:115%;font-size:.62em;opacity:.55;padding-top:1.6em;letter-spacing:.01em}

/* type */
.lead{font-size:1.15em;font-weight:500;line-height:1.3;text-wrap:balance;max-width:20ch}
.lead.gap{margin-top:1.2em}
.hero.fit{white-space:nowrap;overflow-wrap:normal}
.hero{font-family:var(--display);font-weight:900;font-stretch:125%;font-size:4.6em;line-height:.86;letter-spacing:-.045em;font-variant-numeric:tabular-nums;margin:.12em 0 .08em -.04em;overflow-wrap:anywhere}
.hero small{font-size:.32em;font-stretch:100%;font-weight:700;letter-spacing:0;margin-left:.15em}
.hero.name{font-weight:800;font-stretch:62%;font-size:4.4em;line-height:.88;letter-spacing:-.03em;text-wrap:balance}
.hero.diag{font-weight:800;font-stretch:62%;font-size:4.6em;line-height:.86;letter-spacing:-.015em;color:var(--tint);text-wrap:balance}
.hero.sm{font-size:3.4em}
.after{font-size:1em;line-height:1.4;opacity:.85;max-width:26ch;text-wrap:pretty}
.after b{font-weight:600;opacity:1}
.after .count{font-weight:600}

/* stat split */
.split{display:grid;grid-template-columns:repeat(3,1fr);gap:.8em;margin-top:1.4em;padding-top:1em;border-top:1.5px solid var(--soft)}
.split b{display:block;font-family:var(--display);font-weight:800;font-stretch:110%;font-size:1.35em;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.split span{font-size:.72em;opacity:.7;line-height:1.2;display:block;margin-top:.2em}

/* ranked rows */
.rows{list-style:none;display:flex;flex-direction:column;gap:.32em;margin-top:.9em}
.row{position:relative;display:grid;grid-template-columns:1.5em minmax(0,1fr) auto;align-items:baseline;gap:.4em;padding:.55em .75em;border-radius:.7em;overflow:hidden;font-size:.95em}
.row{border-bottom:1.5px solid var(--soft);border-radius:0;padding:.6em 0}
.row::before{content:"";position:absolute;left:0;bottom:-1.5px;height:2.5px;width:calc(var(--w) * 100%);background:var(--tint);border-radius:2px;transform-origin:left;z-index:0}
.row>*{position:relative;z-index:1}
.row .rk{font-family:var(--display);font-weight:700;font-stretch:110%;opacity:.5;font-size:.85em}
.row .nm{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .vl{font-family:var(--display);font-weight:800;font-stretch:110%;font-variant-numeric:tabular-nums}
.row .vl i{font-style:normal;font-family:var(--body);font-weight:400;opacity:.6;font-size:.85em}
.row:first-child{font-size:1.15em}
.row:last-child{border-bottom-color:transparent}
.row.extra{display:none}
.rows.all .row.extra{display:grid}
.more{align-self:flex-start;background:none;border:0;font-size:.75em;font-weight:600;opacity:.7;padding:.6em 0;text-decoration:underline;text-underline-offset:.25em}
.more:hover{opacity:1}

/* avatars: five colorways, swapped where one would vanish into the slide */
.a0{--ab:var(--cobalt);--af:var(--white)}.a1{--ab:var(--pink);--af:var(--ink)}.a2{--ab:var(--ink);--af:var(--lilac)}.a3{--ab:var(--lav);--af:var(--ink)}.a4{--ab:var(--white);--af:var(--cobalt)}
.t-cobalt .a0,.t-stage .a0{--ab:var(--white);--af:var(--cobalt)}.t-cobalt .a4{--ab:var(--lilac);--af:var(--ink)}
.t-pink .a1{--ab:var(--white);--af:var(--pink)}
.t-ink .a2,.t-night .a2{--ab:var(--lilac);--af:var(--ink)}
.t-lav .a3,.t-lilac .a3{--ab:var(--white);--af:var(--ink)}.t-lilac .a4,.t-white .a4{--ab:var(--lilac);--af:var(--cobalt)}
/* avatars */
.av{display:inline-grid;place-items:center;width:2.6em;height:2.6em;border-radius:50%;background:var(--ab);color:var(--af);font-family:var(--display);font-weight:800;font-stretch:115%;font-size:1em;letter-spacing:-.02em;box-shadow:0 0 0 .18em var(--bg)}
.av.xl{width:5.2em;height:5.2em;font-size:1.5em;margin-bottom:auto;box-shadow:0 1em 2.4em -1em rgba(36,16,56,.45)}
.stack{display:flex;margin-bottom:auto;padding-left:.7em}
.stack .av{width:3.6em;height:3.6em;margin-left:-.7em;font-size:1.05em}
.stack .av:nth-child(1){width:4.6em;height:4.6em;z-index:5}
.stack .av:nth-child(2){z-index:4}.stack .av:nth-child(3){z-index:3}.stack .av:nth-child(4){z-index:2}.stack .av:nth-child(5){z-index:1}

/* message pile */
.pile{display:flex;flex-wrap:wrap;gap:.3em;margin-bottom:auto;align-content:flex-start;max-height:46%;overflow:hidden}
.pile i{width:1.05em;height:.75em;border-radius:.4em .4em .4em .12em;background:var(--soft);background:color-mix(in srgb,var(--fg) 16%,transparent)}
.pile i.s{background:var(--cobalt);border-radius:.4em .4em .12em .4em}

/* redacted text */
.redact{display:flex;flex-direction:column;gap:.55em;margin-bottom:auto}
.redact i{height:.8em;width:var(--w);border-radius:.4em;background:var(--soft);background:color-mix(in srgb,var(--fg) 12%,transparent)}
.redact i:nth-child(4n){background:var(--cobalt);opacity:.85}

/* streak chain */
.chain{display:grid;grid-template-columns:repeat(15,1fr);gap:.3em;margin-bottom:auto}
.chain i{aspect-ratio:1;border-radius:.25em;background:var(--cobalt)}

/* stars */
.stars{position:absolute;inset:4em 0 50% 0;pointer-events:none}
.stars i{position:absolute;width:.25em;height:.25em;border-radius:50%;background:var(--lilac);box-shadow:0 0 .6em var(--lilac);animation:twinkle 3s infinite;animation-delay:calc(var(--d) * -.4s)}
@keyframes twinkle{0%,100%{opacity:.25}50%{opacity:1}}

/* year sparkline */
.spark{display:flex;align-items:flex-end;gap:1px;height:9em;margin-bottom:auto;padding-bottom:1.4em}
.spark i{flex:1;height:var(--h);background:var(--ink);opacity:.28;border-radius:1px 1px 0 0}
.spark i.pk{opacity:1;background:var(--white);box-shadow:0 0 0 2px var(--ink)}

/* sticker */
.sticker.big{font-size:6em}
.sticker{margin-bottom:auto;align-self:flex-start;font-size:4.2em;line-height:1;width:1.7em;height:1.7em;display:grid;place-items:center;border-radius:50%;background:var(--soft);transform:rotate(-8deg)}

/* typing */
.typing{display:flex;gap:.3em;padding:.85em 1em;font-size:1.6em}
.typing i{width:.42em;height:.42em;border-radius:50%;background:currentColor;opacity:.35;animation:blink 1.2s infinite}
.typing i:nth-child(2){animation-delay:.2s}.typing i:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,60%,100%{opacity:.3;transform:none}30%{opacity:1;transform:translateY(-.12em)}}

/* clock */
.clock{position:relative;width:11em;height:11em;border-radius:50%;margin-bottom:auto;background:var(--soft)}
.clock i{position:absolute;left:50%;top:50%;width:.22em;height:.9em;margin:-.45em 0 0 -.11em;background:currentColor;opacity:.4;border-radius:.2em;transform:rotate(var(--t)) translateY(-4.6em)}
.clock b{position:absolute;left:50%;top:50%;width:.36em;height:4.2em;margin-left:-.18em;background:var(--pink);border-radius:.3em;transform-origin:50% 0;transform:rotate(calc(var(--a) + 180deg));box-shadow:0 0 1.2em var(--pink)}
.clock u{position:absolute;left:50%;top:50%;width:.9em;height:.9em;margin:-.45em;border-radius:50%;background:var(--pink)}

/* versus */
.vs{display:flex;flex-direction:column;gap:.5em;margin-top:1.2em}
.vs div{display:flex;justify-content:space-between;align-items:center;font-weight:500;padding:.55em .8em;border-radius:.9em;background:var(--fg);color:var(--bg);width:max(9em, calc(var(--w) * 100%));transform-origin:left}
.vs div:last-child{background:var(--soft);color:var(--fg)}
.vs b{font-family:var(--display);font-weight:800;font-stretch:110%;font-variant-numeric:tabular-nums;margin-left:1em}

/* bubbles */
.thread{display:flex;flex-direction:column;gap:.3em;margin-bottom:auto}
.bub{max-width:80%;padding:.5em .8em;border-radius:1.1em;font-size:1em;line-height:1.3;width:fit-content}
.bub.r{background:var(--soft);border-bottom-left-radius:.3em}
.bub.s{align-self:flex-end;background:var(--fg);color:var(--bg);border-bottom-right-radius:.3em}
.thread.big .bub{font-size:1.4em}

/* intro */
.intro{display:flex;flex-direction:column;flex:1}
.stretch{font-family:var(--display);line-height:.82;letter-spacing:-.04em;margin-bottom:auto}
.stretch span{display:block}
.stretch span:first-child{font-weight:800;font-stretch:58%;font-size:3.6em;white-space:nowrap}
.stretch span:last-child{font-weight:900;font-stretch:150%;font-size:3.4em;margin-left:-.05em;white-space:nowrap}
.intro .thread{margin:0 0 1.2em}
.hint{font-size:.85em;opacity:.7;font-weight:500}

/* year dots */
.year{display:flex;flex-direction:column;gap:.34em;margin:1em 0 .2em}
.mrow{display:grid;grid-template-columns:2em minmax(0,1fr);align-items:center}
.mrow span{font-size:.6em;opacity:.6;font-weight:500}
.dots{display:grid;grid-template-columns:repeat(31,1fr);gap:.14em}
.dots i{aspect-ratio:1;border-radius:50%;background:currentColor;opacity:.12}
.dots i.na{opacity:0}
.dots i.fut{opacity:.04}
.dots i.l1{opacity:.3}.dots i.l2{opacity:.55}.dots i.l3{opacity:.85}
.dots i.l4{opacity:1;background:var(--pink);box-shadow:0 0 .5em var(--pink)}
.tip{position:fixed;pointer-events:none;background:var(--white);color:var(--ink);font:500 13px var(--body);padding:6px 10px;border-radius:999px;transform:translate(-50%,-140%);opacity:0;transition:opacity .15s;z-index:20;white-space:nowrap;box-shadow:0 6px 20px rgba(0,0,0,.25)}

/* moon */
.moon{position:absolute;top:4.6em;right:1.6em;width:4.5em;height:4.5em;border-radius:50%;box-shadow:inset -1.1em .5em 0 0 var(--pink);filter:drop-shadow(0 0 1.4em rgba(255,95,162,.45));transform:rotate(-20deg)}

/* emoji */
.emoji{display:flex;flex-wrap:wrap;gap:.1em .25em;font-size:3.2em;line-height:1.15;margin:.2em 0 .3em}
.emoji span{display:inline-block}

/* duo */
.duo{margin-top:1.1em}
.duo+.duo{padding-top:1.1em;border-top:1.5px solid var(--soft)}

/* summary */
.t-stage .tilt{perspective:1200px}
.summary{transform-style:preserve-3d;transition:transform .5s var(--ease);background:linear-gradient(160deg,#4A62FF 0%,var(--cobalt) 45%,#2236D9 100%)}
.summary .sheen{position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at var(--mx,30%) var(--my,20%),rgba(255,255,255,.28),transparent 45%);mix-blend-mode:soft-light;z-index:2}
.summary .hero{font-size:4.2em}
.grid4{display:grid;grid-template-columns:1fr 1fr;gap:.9em 1em;margin-top:1.3em;padding-top:1.1em;border-top:1.5px solid var(--soft)}
.grid4 dt{font-size:.7em;opacity:.7}
.grid4 dd{font-family:var(--display);font-weight:800;font-stretch:115%;font-size:1.5em;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.diag-sm{font-family:var(--display);font-weight:900;font-stretch:55%;font-size:2.4em;line-height:.9;margin-top:.7em;color:#FFC2DC}
.top3{font-size:.85em;opacity:.85;margin-top:.5em}

/* chrome: progress + controls, sized to the card */
.top{position:fixed;left:50%;transform:translateX(-50%);width:var(--cw);top:calc((100dvh - var(--ch)) / 2);padding:calc(var(--cw)*.035) calc(var(--cw)*.07) 0;z-index:10;color:var(--chrome,#fff);transition:color .4s}
.bars{display:flex;gap:4px}
.bars button{flex:1;height:3px;border:0;border-radius:3px;background:currentColor;opacity:.25;padding:0;position:relative}
.bars button::after{content:"";position:absolute;inset:-10px 0}
.bars button.done{opacity:.9}
.ctl{display:flex;justify-content:space-between;align-items:center;margin-top:12px;font-size:13px;font-weight:500}
.ctl .brand{font-family:var(--display);font-weight:800;font-stretch:120%;font-size:14px;opacity:.85}
.pills{display:flex;gap:6px}
.pill{display:inline-flex;align-items:center;gap:6px;border:0;border-radius:999px;padding:7px 12px;background:color-mix(in srgb,currentColor 14%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:transform .2s var(--spring),background .2s}
.pill:hover{background:color-mix(in srgb,currentColor 22%,transparent)}
.pill:active{transform:scale(.94)}
.pill svg{width:14px;height:14px}
.eq{display:inline-flex;gap:2px;align-items:center;height:12px}
.eq i{width:2px;height:4px;background:currentColor;border-radius:1px;transition:height .2s}
.sound-on .eq i{animation:eq .9s infinite ease-in-out}
.sound-on .eq i:nth-child(2){animation-delay:.15s}.sound-on .eq i:nth-child(3){animation-delay:.3s}
@keyframes eq{0%,100%{height:3px}50%{height:12px}}

/* entrance choreography, replayed on each slide */
.on .lead,.on .after,.on .split,.on .more,.on .mark{animation:rise .7s var(--ease) both}
.on .lead{animation-delay:.05s}
.on .hero{animation:heroIn .8s var(--spring) both;animation-delay:.15s}
.on .after{animation-delay:.45s}
.on .split,.on .grid4{animation:rise .7s var(--ease) both;animation-delay:.6s}
.on .row{animation:rowIn .55s var(--ease) both;animation-delay:calc(.2s + var(--d) * 70ms)}
.on .row::before{animation:grow .9s var(--ease) both;animation-delay:calc(.35s + var(--d) * 70ms)}
.on .bub{animation:pop .45s var(--spring) both}
.on .bub:nth-child(2){animation-delay:.55s}.on .bub:nth-child(3){animation-delay:1.1s}
.on .intro .a1{animation-delay:.9s}.on .intro .a2{animation-delay:1.6s}.on .intro .a3{animation-delay:2.3s}
.on .intro .a4{animation:rise .6s var(--ease) both;animation-delay:2.9s}
.on .stretch span:last-child{animation:stretch 1.4s var(--ease) both}
.on .stretch span:first-child{animation:rise .8s var(--ease) both}
.on .emoji span{animation:pop .5s var(--spring) both;animation-delay:calc(.25s + var(--d) * 90ms)}
.on .dots i{animation:dot .5s var(--ease) both;animation-delay:calc(var(--r, 0) * 45ms)}
.on .moon{animation:moon 1.4s var(--ease) both}
.on .redact i{animation:grow .8s var(--ease) both;transform-origin:left;animation-delay:calc(var(--k, 0) * 60ms)}
.on .chain i{animation:pop .3s var(--spring) both;animation-delay:calc(var(--k, 0) * 12ms)}
.on .spark i{animation:barUp .7s var(--ease) both;transform-origin:bottom;animation-delay:calc(var(--k, 0) * 2ms)}
@keyframes barUp{from{transform:scaleY(0)}}
.on .pile i{animation:pop .35s var(--spring) both;animation-delay:calc(var(--d, 0) * 1ms)}
.on .av{animation:pop .6s var(--spring) both;animation-delay:calc(.1s + var(--i, 0) * 90ms)}
.on .sticker{animation:sticker .8s var(--spring) both}
.on .clock b{animation:hand 1.6s var(--spring) both}
.on .vs div{animation:grow .9s var(--ease) both;animation-delay:.5s}
.on .vs div:last-child{animation-delay:.65s}
@keyframes sticker{from{opacity:0;transform:rotate(-40deg) scale(.4)}to{opacity:1;transform:rotate(-8deg)}}
@keyframes hand{from{transform:rotate(180deg)}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:var(--o,1);transform:none}}
@keyframes heroIn{from{opacity:0;transform:translateY(24px) scale(.94);filter:blur(6px)}to{opacity:1;transform:none;filter:none}}
@keyframes rowIn{from{opacity:0;transform:translateX(-12px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes pop{from{opacity:0;transform:translateY(8px) scale(.9)}to{opacity:1;transform:none}}
@keyframes stretch{from{font-stretch:50%;opacity:0}30%{opacity:1}to{font-stretch:150%}}
@keyframes dot{from{transform:scale(0)}to{transform:none}}
@keyframes moon{from{opacity:0;transform:rotate(-60deg) translateY(1em)}to{opacity:1;transform:rotate(-20deg)}}
.after{--o:.85}

/* saving: freeze everything at its final frame */
.capturing *, .capturing *::before{animation:none !important;transition:none !important}

@media (max-width:540px){
  :root{--cw:100vw;--ch:100dvh}
  .card{border-radius:0;box-shadow:none;padding-top:max(5.4em, calc(env(safe-area-inset-top) + 4.6em));padding-bottom:max(1.3em, env(safe-area-inset-bottom))}
  .top{padding-top:max(10px, env(safe-area-inset-top))}
}
@media (prefers-reduced-motion:reduce){
  *,*::before{animation:none !important;transition-duration:.01s !important}
}
</style>
</head>
<body>
<div class="top" id="top">
  <div class="bars" id="bars" role="tablist" aria-label="Slides"></div>
  <div class="ctl">
    <span class="brand">wrap2026</span>
    <div class="pills">
      <button class="pill" id="sound" aria-pressed="false"><span class="eq" aria-hidden="true"><i></i><i></i><i></i></span><span id="soundLbl">Sound off</span></button>
      <button class="pill" id="save"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg><span id="saveLbl">Save image</span></button>
    </div>
  </div>
</div>
<main class="deck" id="deck">__SLIDES__</main>
<div class="tip" id="tip"></div>
<label id="hapticLbl" style="position:fixed;left:-99px;top:-99px;opacity:0" aria-hidden="true"><input type="checkbox" switch tabindex="-1"></label>

<script>
(() => {
const FILE = '__FILE__';
const deck = document.getElementById('deck');
const slides = [...deck.querySelectorAll('.slide')];
const bars = document.getElementById('bars');
const top = document.getElementById('top');
const dark = new Set(['t-cobalt','t-ink','t-night','t-stage']);
let cur = -1;

// fit text to the card width (numbers and the intro title)
function fit(el, max) {
  el.style.fontSize = '';
  const base = parseFloat(getComputedStyle(el).fontSize), w = el.parentElement.clientWidth;
  el.style.fontSize = base + 'px';
  const ratio = w / el.scrollWidth;
  el.style.fontSize = (max ? Math.min(base * ratio, base * max) : Math.min(base, base * ratio)) + 'px';
}
function fitAll() {
  document.querySelectorAll('.stretch span').forEach(e => fit(e, 3));
  document.querySelectorAll('.hero.fit').forEach(e => fit(e));
}
document.querySelectorAll('.hero').forEach(h => { if (!h.classList.contains('name') && !h.classList.contains('diag')) h.classList.add('fit'); });
document.querySelectorAll('.redact, .chain, .spark').forEach(p => [...p.children].forEach((c, k) => c.style.setProperty('--k', k)));
document.querySelectorAll('.pile i').forEach(i => i.style.setProperty('--d', Math.round(Math.random() * 900)));
document.querySelectorAll('.stack, .slide .body').forEach(p => p.querySelectorAll(':scope > .av, :scope > .stack > .av').forEach((a, k) => a.style.setProperty('--i', k)));
(document.fonts ? document.fonts.ready : Promise.resolve()).then(fitAll);
addEventListener('resize', fitAll);

// dot rows stagger by month
document.querySelectorAll('.mrow').forEach((r, i) => r.querySelectorAll('i').forEach(d => d.style.setProperty('--r', i)));

slides.forEach((s, i) => {
  const b = document.createElement('button');
  b.setAttribute('aria-label', 'Slide ' + (i + 1));
  b.addEventListener('click', e => { e.stopPropagation(); go(i); });
  bars.appendChild(b);
});

// sound: one soft note per slide, climbing a pentatonic scale
let ctx = null, soundOn = false;
try { soundOn = localStorage.getItem('wrap-sound') === '1'; } catch (_) {}
const scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24];
function note(i) {
  if (!soundOn) return;
  ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
  const t = ctx.currentTime, f = 392 * Math.pow(2, scale[i % scale.length] / 12);
  [1, 2].forEach((h, k) => {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = k ? 'triangle' : 'sine'; o.frequency.value = f * h;
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(k ? .012 : .05, t + .012);
    g.gain.exponentialRampToValueAtTime(.0001, t + .5);
    o.connect(g).connect(ctx.destination); o.start(t); o.stop(t + .55);
  });
}
const soundBtn = document.getElementById('sound');
function paintSound() {
  document.body.classList.toggle('sound-on', soundOn);
  soundBtn.setAttribute('aria-pressed', soundOn);
  document.getElementById('soundLbl').textContent = soundOn ? 'Sound on' : 'Sound off';
}
soundBtn.addEventListener('click', e => {
  e.stopPropagation(); soundOn = !soundOn; paintSound();
  try { localStorage.setItem('wrap-sound', soundOn ? '1' : '0'); } catch (_) {}
  note(cur); buzz();
});
paintSound();

// haptics: Android vibrate, iOS switch-toggle tick
const hap = document.querySelector('#hapticLbl');
function buzz() {
  if (navigator.vibrate) { navigator.vibrate(8); return; }
  if (matchMedia('(pointer:coarse)').matches) hap.click();
}

// count-up for big numbers
function countUp(el) {
  const to = parseFloat(el.dataset.to), dec = el.dataset.fmt === 'dec', sfx = el.dataset.suffix || '';
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || document.body.classList.contains('capturing')) return;
  const t0 = performance.now(), dur = 1300;
  const fmt = v => (dec ? v.toFixed(1) : Math.round(v).toLocaleString('en-US')) + sfx;
  (function f(t) {
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(2, -10 * p);
    el.textContent = fmt(p >= 1 ? to : to * e);
    if (p < 1 && el.closest('.slide.on')) requestAnimationFrame(f); else el.textContent = fmt(to);
  })(t0);
}

function go(i, quiet) {
  if (i < 0 || i >= slides.length || i === cur) return;
  slides.forEach((s, k) => { s.classList.toggle('on', k === i); s.classList.toggle('past', k < i); });
  [...bars.children].forEach((b, k) => { b.classList.toggle('done', k <= i); b.setAttribute('aria-current', k === i ? 'step' : 'false'); });
  cur = i;
  const s = slides[i];
  const theme = [...s.classList].find(c => c.startsWith('t-'));
  top.style.setProperty('--chrome', dark.has(theme) ? '#fff' : '#241038');
  s.querySelectorAll('.count').forEach(countUp);
  if (!quiet) { note(i); buzz(); }
  try { history.replaceState(null, '', '#' + s.dataset.name); } catch (_) {}
}

// tap left third to go back, the rest to go forward; swipe works too
let sx = null, sy = null;
deck.addEventListener('pointerdown', e => { sx = e.clientX; sy = e.clientY; });
deck.addEventListener('pointerup', e => {
  if (sx === null) return;
  const dx = e.clientX - sx, dy = e.clientY - sy; sx = null;
  if (e.target.closest('button, a, .tilt')) return;
  if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) { go(cur + (dx < 0 ? 1 : -1)); return; }
  if (Math.abs(dx) < 8 && Math.abs(dy) < 8) go(e.clientX < innerWidth * .3 ? cur - 1 : cur + 1);
});
document.addEventListener('keydown', e => {
  if (['ArrowRight', ' ', 'PageDown'].includes(e.key)) { e.preventDefault(); go(cur + 1); }
  if (['ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); go(cur - 1); }
  if (e.key === 'Home') go(0);
  if (e.key === 'End') go(slides.length - 1);
});

// show all 10
document.querySelectorAll('[data-more]').forEach(b => b.addEventListener('click', e => {
  e.stopPropagation();
  const list = b.closest('.body').querySelector('.rows');
  const all = list.classList.toggle('all');
  b.textContent = all ? 'Show top 5' : b.textContent.replace('Show top 5', '');
  if (!all) b.textContent = 'Show all ' + list.children.length;
  buzz();
}));

// day tooltips
const tip = document.getElementById('tip');
document.querySelectorAll('.dots i[data-tip]').forEach(d => {
  d.addEventListener('pointerenter', e => { if (e.pointerType !== 'mouse') return; const r = d.getBoundingClientRect(); tip.textContent = d.dataset.tip; tip.style.left = (r.left + r.width / 2) + 'px'; tip.style.top = r.top + 'px'; tip.style.opacity = 1; });
  d.addEventListener('pointerleave', () => tip.style.opacity = 0);
});

// summary card tilts toward the pointer
const tilt = document.querySelector('.tilt');
if (tilt) {
  const card = tilt.querySelector('.card');
  tilt.addEventListener('pointermove', e => {
    const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    card.style.transition = 'transform .08s linear';
    card.style.transform = `rotateY(${(x - .5) * 14}deg) rotateX(${(.5 - y) * 14}deg)`;
    card.style.setProperty('--mx', x * 100 + '%'); card.style.setProperty('--my', y * 100 + '%');
  });
  tilt.addEventListener('pointerleave', () => { card.style.transition = ''; card.style.transform = ''; });
}

// save the current slide as a 1080x1920 image
const saveBtn = document.getElementById('save'), saveLbl = document.getElementById('saveLbl');
saveBtn.addEventListener('click', async e => {
  e.stopPropagation();
  const s = slides[cur], card = s.querySelector('.card');
  if (!window.modernScreenshot) { saveLbl.textContent = 'Offline. Take a screenshot'; setTimeout(() => saveLbl.textContent = 'Save image', 2400); return; }
  saveLbl.textContent = 'Saving'; saveBtn.disabled = true;
  const prev = card.style.transform; card.style.transform = 'none';
  s.classList.add('capturing');
  s.querySelectorAll('.count').forEach(c => c.textContent = (c.dataset.fmt === 'dec' ? (+c.dataset.to).toFixed(1) : (+c.dataset.to).toLocaleString('en-US')) + (c.dataset.suffix || ''));
  try {
    const url = await modernScreenshot.domToPng(card, {
      scale: 1080 / card.offsetWidth,
      filter: n => !(n.classList && n.classList.contains('chrome')),
    });
    const a = document.createElement('a'); a.href = url; a.download = `${FILE}_${s.dataset.name}.png`; a.click();
    saveLbl.textContent = 'Saved'; buzz();
  } catch (err) { console.error(err); saveLbl.textContent = 'Could not save'; }
  s.classList.remove('capturing'); card.style.transform = prev;
  setTimeout(() => { saveLbl.textContent = 'Save image'; saveBtn.disabled = false; }, 1800);
});

if (location.search.includes('still')) document.body.classList.add('capturing');
const start = slides.findIndex(s => '#' + s.dataset.name === location.hash);
go(start > 0 ? start : 0, true);
})();
</script>
</body></html>'''
