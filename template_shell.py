TEMPLATE = r'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>__TITLE__</title>
<meta name="theme-color" content="#160A26">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'><rect x='4' y='10' width='56' height='40' rx='20' fill='%232F4BFF'/><path d='M14 44 L8 58 L26 48Z' fill='%232F4BFF'/></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link crossorigin="anonymous" href="https://fonts.googleapis.com/css2?family=Anybody:wdth,wght@50..150,400..900&family=Onest:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/modern-screenshot@4.4.39/dist/index.js"></script>
<style>
:root{
  --ink:#241038; --night:#160A26; --lilac:#EEE8FF; --lav:#DCD3F5;
  --cobalt:#2F4BFF; --pink:#FF5FA2; --white:#FFFFFF;
  --cw:min(100vw, calc(92dvh * 9 / 16));
  --ch:calc(var(--cw) * 16 / 9);
  --display:'Anybody',system-ui,sans-serif;
  --body:'Onest',system-ui,sans-serif;
  --ease:cubic-bezier(.23,1,.32,1);
  --spring:cubic-bezier(.3,1.4,.5,1);
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overscroll-behavior:none}
html{-webkit-text-size-adjust:100%}
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
.slide{position:absolute;inset:0;display:grid;place-items:center;opacity:0;visibility:hidden;transform:translateX(5%) scale(.97);transition:opacity .2s var(--ease),transform .3s var(--ease),visibility 0s .3s}
.slide.past{transform:translateX(-5%) scale(.97)}
.slide.on{opacity:1;visibility:visible;transform:none;transition:opacity .3s var(--ease),transform .35s var(--ease),visibility 0s}
.card{position:relative;width:var(--cw);height:var(--ch);border-radius:calc(var(--cw) * .075);background:var(--bg);color:var(--fg);font-size:calc(var(--cw) / 22);padding:5.2em 1.6em 1.3em;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 30px 80px -30px rgba(0,0,0,.5)}
.body{flex:1;display:flex;flex-direction:column;gap:.2em;min-height:0;padding-bottom:1em}
/* vertical rhythm: one rule for every slide. The content block (top visual + text) is centered between the
   chrome and the footer. The spacers shrink to 0 when content is tall, so it never rides up under the chrome. */
.body::before,.body::after{content:"";flex:1 1 0}
.body:has(>.intro)::before,.body:has(>.intro)::after{content:none}
.body>:is(.pile,.redact,.chain,.spark,.sticker,.stack,.av.xl,.thread,.clock,.wave,.share,.tiles,.ringing,.waffle,.pies,.notes,.cal,.cols,.lag,.who){margin-bottom:1.1em}
.body>.spark{padding-bottom:0;flex-shrink:0}
.body:has(>.rows)>.spark{height:5em}
.mark{display:flex;justify-content:space-between;font-family:var(--display);font-weight:700;font-stretch:115%;font-variation-settings:"wdth" 115;font-size:.62em;opacity:.85;padding-top:1.6em;letter-spacing:.01em}

/* type */
.lead{font-size:1.15em;font-weight:500;line-height:1.3;text-wrap:balance;max-width:20ch}
.lead.gap{margin-top:1.2em}
.hero.fit{white-space:nowrap;overflow-wrap:normal}
.hero{font-family:var(--display);font-weight:900;font-stretch:125%;font-variation-settings:"wdth" 125;font-size:4.6em;line-height:.86;letter-spacing:-.045em;font-variant-numeric:tabular-nums;margin:.12em 0 .08em -.04em;overflow-wrap:anywhere}
.hero small{font-size:.32em;font-stretch:100%;font-variation-settings:"wdth" 100;font-weight:700;letter-spacing:0;margin-left:.15em}
.hero.name{font-weight:800;font-stretch:62%;font-variation-settings:"wdth" 62;font-size:4.4em;line-height:.88;letter-spacing:-.03em;text-wrap:balance;overflow-wrap:normal}
.hero.diag{font-weight:800;font-stretch:62%;font-variation-settings:"wdth" 62;font-size:4.6em;line-height:.86;letter-spacing:-.015em;color:var(--tint);text-wrap:balance;overflow-wrap:normal}
.hero.sm{font-size:3.4em}
.after{font-size:1em;line-height:1.4;opacity:.85;max-width:26ch;text-wrap:pretty;overflow-wrap:break-word}
.after b{font-weight:600;opacity:1}
.after .count{font-weight:600;font-variant-numeric:tabular-nums}

/* stat split */
.split{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8em;margin-top:1.4em;padding-top:1em;border-top:1.5px solid var(--soft)}
.split b{display:block;font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-size:1.35em;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.split span{font-size:.72em;opacity:.7;line-height:1.2;display:block;margin-top:.2em}

/* ranked rows */
.rows{list-style:none;display:flex;flex-direction:column;gap:.32em;margin-top:.9em}
.row{position:relative;display:grid;grid-template-columns:1.5em minmax(0,1fr) auto;align-items:baseline;gap:.4em;padding:.55em .75em;border-radius:.7em;overflow:hidden;font-size:.95em}
.row{border-bottom:1.5px solid var(--soft);border-radius:0;padding:.6em 0}
.row::before{content:"";position:absolute;left:0;bottom:-1.5px;height:2.5px;width:calc(var(--w) * 100%);background:var(--tint);border-radius:2px;transform-origin:left;z-index:0}
.row>*{position:relative;z-index:1}
.row .rk{font-family:var(--display);font-weight:700;font-stretch:110%;font-variation-settings:"wdth" 110;opacity:.85;font-size:.85em}
.row .nm{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .vl{font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-variant-numeric:tabular-nums}
.row .vl i{font-style:normal;font-family:var(--body);font-weight:400;opacity:.85;font-size:.85em}
.row:first-child{font-size:1.15em}
.row:last-child{border-bottom-color:transparent}
.row.extra{display:none}
.rows.all .row.extra{display:grid}
/* expanded to 10: compact rows, decoration steps aside, and the body scrolls inside the card as a last resort */
.rows.all{gap:0;margin-top:.6em}
.rows.all .row{padding:.34em 0;font-size:.85em}
.rows.all .row:first-child{padding:.45em 0;font-size:1em}
.body:has(.rows.all)>:is(.stack,.spark,.thread,.sticker,.pile,.av.xl){display:none}
.body:has(.rows.all){overflow-y:auto;overscroll-behavior:contain;scrollbar-width:none;margin:0 -.3em;padding-left:.3em;padding-right:.3em}
.body:has(.rows.all)::-webkit-scrollbar{display:none}
.rows.tight{margin-top:.5em;gap:.1em}
.rows.tight .row{padding:.4em 0}
.rows.tight .row:first-child{font-size:1em}
.more{align-self:flex-start;background:none;border:0;font-size:.75em;font-weight:600;opacity:.85;padding:.6em 0;text-decoration:underline;text-underline-offset:.25em}
@media (hover:hover) and (pointer:fine){.more:hover{opacity:1}}

/* avatars: five colorways, swapped where one would vanish into the slide */
.a0{--ab:var(--cobalt);--af:var(--white)}.a1{--ab:var(--pink);--af:var(--ink)}.a2{--ab:var(--ink);--af:var(--lilac)}.a3{--ab:var(--lav);--af:var(--ink)}.a4{--ab:var(--white);--af:var(--cobalt)}
.t-cobalt .a0,.t-stage .a0{--ab:var(--white);--af:var(--cobalt)}.t-cobalt .a4{--ab:var(--lilac);--af:var(--ink)}
.t-pink .a1{--ab:var(--white);--af:var(--ink)}
.t-ink .a2,.t-night .a2{--ab:var(--lilac);--af:var(--ink)}
.t-lav .a3,.t-lilac .a3{--ab:var(--white);--af:var(--ink)}.t-lilac .a4,.t-white .a4{--ab:var(--cobalt);--af:var(--white)}
/* avatars */
.av{display:inline-grid;place-items:center;width:2.6em;height:2.6em;border-radius:50%;background:var(--ab);color:var(--af);font-family:var(--display);font-weight:800;font-stretch:115%;font-variation-settings:"wdth" 115;font-size:1em;letter-spacing:-.02em;box-shadow:0 0 0 .18em var(--bg);flex:none}
.av .ae{font-size:1.15em;letter-spacing:0}
.av .ag{width:1.15em;height:1.15em}
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
.spark{display:flex;align-items:flex-end;gap:0;height:9em;margin-bottom:auto;padding-bottom:1.4em}
.spark i{flex:1;height:var(--h);background:var(--ink);opacity:.28;border-radius:1px 1px 0 0}
.spark i.pk{opacity:1;background:var(--white);box-shadow:0 0 0 2px var(--ink)}
/* day graph: hover or drag reads a day; the label sits above the bars */
.spark[data-c]{position:relative;touch-action:none;cursor:crosshair;margin-top:2.2em}
.spark .sl{position:absolute;left:0;top:-.5em;translate:0 -100%;padding:.3em .7em;border-radius:999px;background:var(--fg);color:var(--bg);font-size:.72em;font-weight:600;white-space:nowrap;font-variant-numeric:tabular-nums;pointer-events:none;transition:opacity .15s var(--ease)}
.spark i.cur{opacity:1}

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
.vs div{position:relative;isolation:isolate;display:flex;justify-content:space-between;align-items:center;font-weight:500;padding:.55em .8em;border-radius:.9em;color:var(--bg);width:max(11em, calc(var(--w) * 100%));max-width:100%}
.vs div::before{content:"";position:absolute;inset:0;z-index:-1;border-radius:inherit;background:var(--fg);transform-origin:left}
.vs span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vs div:last-child{color:var(--fg)}
.vs div:last-child::before{background:var(--soft)}
.vs b{flex:none;font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-variant-numeric:tabular-nums;margin-left:1em}

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
.stretch span:first-child{font-weight:800;font-stretch:58%;font-variation-settings:"wdth" 58;font-size:3.6em;white-space:nowrap}
.stretch span:last-child{font-weight:900;font-stretch:150%;font-variation-settings:"wdth" 150;font-size:3.4em;margin-left:-.05em;white-space:nowrap}
.intro .thread{margin:0 0 1.2em}
.hint{font-size:.85em;opacity:.85;font-weight:500}

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
.summary{transform-style:preserve-3d;transition:transform .5s var(--ease);background:var(--pbg)}
/* poster palettes: t-poster-a (cobalt, default) to d; JS picks POSTER (or ?poster=b) */
.t-stage,.t-poster-a{--pbg:linear-gradient(160deg,#4A62FF 0%,var(--cobalt) 45%,#2236D9 100%);--acc:#FFC2DC;--bar:var(--white);--bo:.4;--pk:var(--pink);--cbg:var(--white);--cfg:var(--cobalt)}
.t-poster-b{--bg:var(--ink);--fg:var(--lilac);--soft:rgba(238,232,255,.1);--tint:var(--pink);--pbg:linear-gradient(160deg,var(--ink) 0%,var(--night) 100%);--acc:var(--pink);--bar:var(--lilac);--bo:.35;--pk:var(--pink);--cbg:var(--pink);--cfg:var(--ink)}
.t-poster-c{--bg:var(--lilac);--fg:var(--ink);--soft:rgba(36,16,56,.08);--tint:var(--cobalt);--pbg:var(--lilac);--acc:var(--cobalt);--bar:var(--ink);--bo:.25;--pk:var(--cobalt);--cbg:var(--cobalt);--cfg:var(--white)}
.t-poster-d{--bg:var(--pink);--fg:var(--ink);--soft:rgba(36,16,56,.1);--tint:var(--white);--pbg:var(--pink);--acc:var(--ink);--bar:var(--ink);--bo:.25;--pk:var(--ink);--cbg:var(--ink);--cfg:var(--pink)}
.summary .sheen{position:absolute;inset:0;pointer-events:none;background:radial-gradient(circle at var(--mx,30%) var(--my,20%),rgba(255,255,255,.28),transparent 45%);mix-blend-mode:soft-light;z-index:2}
.summary .hero{font-size:4.2em}
.grid4{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.9em 1em;margin-top:1.3em;padding-top:1.1em;border-top:1.5px solid var(--soft)}
.grid4 dt{font-size:.7em;opacity:.85}
.grid4 dd{font-family:var(--display);font-weight:800;font-stretch:115%;font-variation-settings:"wdth" 115;font-size:1.5em;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.diag-sm{font-family:var(--display);font-weight:900;font-stretch:55%;font-variation-settings:"wdth" 55;font-size:2.4em;line-height:.9;margin-top:.7em;color:#FFC2DC}
.top3{font-size:.85em;opacity:.85;margin-top:.5em}
/* summary poster: the slide people post */
.ptitle{font-family:var(--display);font-weight:800;line-height:.9;letter-spacing:-.03em;white-space:nowrap;font-size:2.4em}
.ptitle span:first-child{font-stretch:58%;font-variation-settings:"wdth" 58}
.ptitle span:last-child{font-weight:900;font-stretch:150%;font-variation-settings:"wdth" 150;margin-left:.12em}
/* poster layout: title, graph and total on top; personality, #1 and three stats at the bottom */
.poster .body::before,.poster .body::after{content:none}
.poster .body{padding-bottom:1em}
.poster .hero small{opacity:.85}
.pwave{height:5em;padding:0;margin:1.6em 0 .5em}
.poster .pwave{flex-shrink:1;min-height:2.6em;margin-top:1.2em}
.pwave i{background:var(--bar);opacity:var(--bo)}
.pwave i.pk{background:var(--pk);opacity:1;box-shadow:none}
.pwave .sl{opacity:0}.pwave.hot .sl{opacity:1}
.pmeta{font-size:.78em;font-weight:500;opacity:.85;margin-top:.15em}
.poster .ptitle{font-size:1.9em;margin-bottom:auto}
/* white at .85 on the light end of the cobalt gradient is 3.8:1; full white is 4.7:1 */
.t-poster-a .poster :is(.pmeta,.one span,.stats3 dt,.hero small){opacity:1}
.poster .diag-sm{margin-top:auto;padding-top:.15em;font-size:3.3em;line-height:.88;letter-spacing:-.01em;color:var(--acc);text-wrap:balance}
.one{display:flex;align-items:center;gap:.6em;margin-top:.9em}
.one .av{--ab:var(--fg);--af:var(--bg);width:2.3em;height:2.3em;font-size:.9em;flex:none;box-shadow:none}
.one b{display:block;font-family:var(--display);font-weight:800;font-stretch:75%;font-variation-settings:"wdth" 75;font-size:1.3em;line-height:1.05;letter-spacing:-.01em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.one div{min-width:0}
.one span{font-size:.72em;opacity:.85}
.stats3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8em;margin-top:1.1em}
.stats3 dt{font-size:.68em;opacity:.85}
.stats3 dd{font-family:var(--display);font-weight:800;font-stretch:110%;font-variation-settings:"wdth" 110;font-size:1.15em;font-variant-numeric:tabular-nums;letter-spacing:-.01em;white-space:nowrap}
.poster .mark{opacity:1;gap:1em}
.cta{display:flex;justify-content:center;align-items:center;gap:.5em;margin-top:1.2em;border:0;border-radius:999px;padding:.85em 1em;background:var(--cbg,var(--white));color:var(--cfg,var(--cobalt));font-weight:600;font-size:.9em;transition:transform .15s var(--ease)}
.cta:not(:disabled):active{transform:scale(.96)}
.cta:focus-visible{outline-color:var(--fg)}
.cta svg{width:1.1em;height:1.1em}

/* chrome: progress + controls, sized to the card */
.top{position:fixed;left:50%;transform:translateX(-50%);width:var(--cw);top:calc((100dvh - var(--ch)) / 2);padding:calc(var(--cw)*.035) calc(var(--cw)*.07) 0;z-index:10;color:var(--chrome,#fff);transition:color .3s ease}
.bars{display:flex;gap:4px}
.bars button{flex:1;height:3px;border:0;border-radius:3px;background:currentColor;opacity:.25;padding:0;position:relative}
.bars button::after{content:"";position:absolute;inset:-10px 0}
.bars button.done{opacity:.9}
/* stories-style autoplay (site demo only, ?autoplay): the current bar fills, then the deck moves on */
.auto .bars button.now{opacity:1;background:color-mix(in srgb,currentColor 25%,transparent);overflow:hidden}
.auto .bars button.now::before{content:"";position:absolute;inset:0;border-radius:inherit;background:currentColor;opacity:.9;transform-origin:left;transform:scaleX(0);animation:fill var(--dwell,5s) linear forwards}
.auto.held .bars button.now::before{animation-play-state:paused}
@keyframes fill{to{transform:scaleX(1)}}
.ctl{display:flex;justify-content:space-between;align-items:center;margin-top:12px;font-size:13px;font-weight:500}
.ctl .brand{font-family:var(--display);font-weight:800;font-stretch:120%;font-variation-settings:"wdth" 120;font-size:14px;opacity:.85}
.pills{display:flex;gap:6px}
.pill{display:inline-flex;align-items:center;gap:6px;white-space:nowrap;border:0;border-radius:999px;padding:7px 12px;background:color-mix(in srgb,currentColor 14%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:transform .15s var(--ease),background .2s ease}
@media (hover:hover) and (pointer:fine){.pill:hover{background:color-mix(in srgb,currentColor 22%,transparent)}}
.pill:not(:disabled):active{transform:scale(.96)}
.pill svg{width:14px;height:14px}

/* entrance choreography, replayed on each slide */
.on .lead,.on .after,.on .split,.on .more{animation:rise .5s var(--ease) both}
.on .hero{animation:heroIn .6s var(--spring) both;animation-delay:.08s}
.on .after{animation-delay:.3s}
.on .split,.on .grid4,.on .more{animation:rise .5s var(--ease) both;animation-delay:.38s}
.on .row{animation:rowIn .45s var(--ease) both;animation-delay:calc(.12s + var(--d) * 50ms)}
.on .row::before{animation:grow .6s var(--ease) both;animation-delay:calc(.25s + var(--d) * 50ms)}
.on .bub{animation:pop .45s var(--spring) both}
.on .bub:nth-child(2){animation-delay:.55s}.on .bub:nth-child(3){animation-delay:1.1s}
.on .intro .a1{animation-delay:.9s}.on .intro .a2{animation-delay:1.6s}.on .intro .a3{animation-delay:2.3s}
.on .intro .a4{animation:rise .6s var(--ease) both;animation-delay:2.9s}
.on .stretch span:last-child{animation:stretch 1.4s var(--ease) both}
.on .stretch span:first-child{animation:rise .8s var(--ease) both}
.on .emoji span{animation:pop .5s var(--spring) both;animation-delay:calc(.15s + var(--d) * 60ms)}
.on .dots i{animation:dot .5s var(--ease) both;animation-delay:calc(var(--r, 0) * 45ms)}
.on .moon{animation:moon 1.4s var(--ease) both}
.on .redact i{animation:grow .8s var(--ease) both;transform-origin:left;animation-delay:calc(var(--k, 0) * 60ms)}
.on .chain i{animation:pop .3s var(--spring) both;animation-delay:calc(var(--k, 0) * 12ms)}
.on .spark i{animation:barUp .7s var(--ease) both;transform-origin:bottom;animation-delay:calc(var(--k, 0) * 2ms)}
@keyframes barUp{from{transform:scaleY(0)}}
.on .pile i{animation:pop .35s var(--spring) both;animation-delay:calc(var(--d, 0) * 1ms)}
.on .av{animation:pop .5s var(--spring) both;animation-delay:calc(.08s + var(--i, 0) * 60ms)}
.on .sticker{animation:sticker .8s var(--spring) both}
.on .clock b{animation:hand 1.6s var(--spring) both}
.on .vs div::before{animation:grow .6s var(--ease) both;animation-delay:.3s}
.on .vs div:last-child::before{animation-delay:.38s}
.on .vs div>*{animation:fade .3s var(--ease) both;animation-delay:.5s}
.on .ptitle span:first-child{animation:rise .8s var(--ease) both}
.on .ptitle span:last-child{animation:stretch 1.4s var(--ease) both}
.on .one,.on .stats3,.on .pmeta{animation:rise .5s var(--ease) both;animation-delay:.4s}
.on .cta{animation:rise .5s var(--ease) backwards;animation-delay:.5s}
@keyframes sticker{from{opacity:0;transform:rotate(-40deg) scale(.4)}to{opacity:1;transform:rotate(-8deg)}}
@keyframes hand{from{transform:rotate(180deg)}}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:var(--o,1);transform:none}}
@keyframes heroIn{from{opacity:0;transform:translateY(24px) scale(.94);filter:blur(6px)}to{opacity:1;transform:none;filter:none}}
@keyframes rowIn{from{opacity:0;transform:translateX(-12px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes pop{from{opacity:0;transform:translateY(8px) scale(.9)}to{opacity:1;transform:none}}
@keyframes stretch{from{font-stretch:50%;font-variation-settings:"wdth" 50;opacity:0}30%{opacity:1}to{font-stretch:150%;font-variation-settings:"wdth" 150}}
@keyframes dot{from{opacity:0;transform:scale(.5)}}
@keyframes fade{from{opacity:0}}
@keyframes moon{from{opacity:0;transform:rotate(-60deg) translateY(1em)}to{opacity:1;transform:rotate(-20deg)}}
.after{--o:.85}

/* saving: freeze everything at its final frame */
.capturing *, .capturing *::before{animation:none !important;transition:none !important}
.card.saving{border-radius:0;box-shadow:none}
.fitting *{animation:none !important}

@media (max-width:540px){
  :root{--cw:100vw;--ch:100dvh}
  .card{border-radius:0;box-shadow:none;padding-top:max(5.4em, calc(env(safe-area-inset-top) + 4.6em));padding-bottom:max(1.3em, env(safe-area-inset-bottom))}
  .top{padding-top:max(10px, env(safe-area-inset-top))}
}
@media (prefers-reduced-motion:reduce){
  *,*::before{animation:none !important;transition-duration:.01s !important}
  .slide,.slide.past{transform:none}
  .slide,.slide.on{transition-duration:.3s,.3s,0s !important}
}
.slide:focus{outline:none}
</style>
</head>
<body>
<div class="top" id="top">
  <nav class="bars" id="bars" aria-label="Slides"></nav>
  <div class="ctl">
    <span class="brand">wrap2026</span>
    <div class="pills">
      <button class="pill" id="save" data-act><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg><span class="lbl">Save image</span></button>
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
const dark = new Set(['t-cobalt','t-ink','t-night','t-stage','t-poster-a','t-poster-b']);
// poster palette: a cobalt (default), b ink, c lilac, d pink; ?poster=c previews another
const POSTER = (location.search.match(/[?&]poster=([a-d])\b/) || [, 'a'])[1];
slides.forEach(s => { if (s.dataset.name === 'summary') s.classList.add('t-poster-' + POSTER); });
const themeOf = s => [...s.classList].filter(c => c.startsWith('t-'));
let cur = -1;
const themeMeta = document.querySelector('meta[name="theme-color"]'), phone = matchMedia('(max-width:540px)');
// iOS Safari only applies :active (press feedback) on touch when a touchstart listener exists
document.addEventListener('touchstart', () => {}, { passive: true });

// fit text to the card width (numbers and the intro title)
// measures a hidden copy of the parent, so siblings keep their styles and the real element's entrance animation never restarts
function fit(el, max) {
  el.style.fontSize = '';
  const p = el.parentElement, i = [...p.children].indexOf(el), pc = p.cloneNode(true);
  pc.classList.add('fitting'); pc.setAttribute('aria-hidden', 'true'); pc.removeAttribute('id');
  pc.style.cssText += ';position:absolute;visibility:hidden;left:0;top:0;animation:none;width:' + p.clientWidth + 'px';
  p.after(pc);
  const c = pc.children[i];
  c.style.cssText += ';animation:none;display:inline-block;width:max-content';
  const base = parseFloat(getComputedStyle(c).fontSize), w = p.clientWidth * .97;
  const ratio = w / c.getBoundingClientRect().width;
  pc.remove();
  el.style.fontSize = (max ? Math.min(base * ratio, base * max) : Math.min(base, base * ratio)) + 'px';
}
// long names shrink until every word fits and they take at most three lines; they never split mid-word
function fitName(el) {
  el.style.fontSize = '';
  if (/\p{Extended_Pictographic}/u.test(el.textContent)) el.style.lineHeight = '1.08';
  const cs = () => getComputedStyle(el);
  for (let k = 0; k < 16 && (el.scrollWidth > el.clientWidth + 1 || el.offsetHeight > parseFloat(cs().lineHeight) * 3.2); k++)
    el.style.fontSize = parseFloat(cs().fontSize) * .9 + 'px';
}
function fitAll() {
  document.querySelectorAll('.stretch span').forEach(e => fit(e, 3));
  document.querySelectorAll('.hero.fit').forEach(e => fit(e));
  document.querySelectorAll('.ptitle:not(.poster .ptitle)').forEach(e => fit(e, 3));
  document.querySelectorAll('.split b, .grid4 dd, .stats3 dd').forEach(e => fit(e));
  document.querySelectorAll('.hero.name, .hero.diag, .poster .diag-sm').forEach(fitName);
}
document.querySelectorAll('.hero').forEach(h => { if (!h.classList.contains('name') && !h.classList.contains('diag')) h.classList.add('fit'); });
document.querySelectorAll('.redact, .chain, .spark').forEach(p => [...p.children].forEach((c, k) => c.style.setProperty('--k', k)));
document.querySelectorAll('.pile i').forEach(i => i.style.setProperty('--d', Math.round(Math.random() * 900)));
document.querySelectorAll('.stack, .slide .body').forEach(p => p.querySelectorAll(':scope > .av, :scope > .stack > .av').forEach((a, k) => a.style.setProperty('--i', k)));
(document.fonts ? document.fonts.ready : Promise.resolve()).then(fitAll);
if (document.fonts) document.fonts.addEventListener('loadingdone', fitAll);
addEventListener('resize', fitAll);

// dot rows stagger by month
document.querySelectorAll('.mrow').forEach((r, i) => r.querySelectorAll('i').forEach(d => d.style.setProperty('--r', i)));

slides.forEach((s, i) => {
  const b = document.createElement('button');
  b.setAttribute('aria-label', 'Slide ' + (i + 1) + ' of ' + slides.length);
  s.tabIndex = -1; s.setAttribute('aria-label', (i + 1) + ' of ' + slides.length);
  b.addEventListener('click', e => { e.stopPropagation(); go(i); });
  bars.appendChild(b);
});

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
  const t0 = el._run = performance.now(), dur = 1300;
  const fmt = v => (dec ? v.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : Math.round(v).toLocaleString('en-US')) + sfx;
  (function f(t) {
    if (el._run !== t0) return;
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(2, -10 * p);
    el.textContent = fmt(p >= 1 ? to : to * e);
    if (p < 1 && el.closest('.slide.on')) requestAnimationFrame(f); else el.textContent = fmt(to);
  })(t0);
}

const auto = /[?&]autoplay/.test(location.search) && !matchMedia('(prefers-reduced-motion: reduce)').matches;
function go(i, quiet) {
  if (i < 0 || i >= slides.length || i === cur) return;
  slides.forEach((s, k) => { s.classList.toggle('on', k === i); s.classList.toggle('past', k < i); });
  [...bars.children].forEach((b, k) => { b.classList.toggle('done', auto ? k < i : k <= i); b.classList.toggle('now', auto && k === i); b.setAttribute('aria-current', k === i ? 'step' : 'false'); });
  if (auto) bars.children[i].style.setProperty('--dwell', (/^(intro|summary)$/.test(slides[i].dataset.name) ? 6.5 : 4.5) + 's');
  cur = i;
  const s = slides[i];
  const theme = themeOf(s).pop();
  top.style.setProperty('--chrome', dark.has(theme) ? '#fff' : '#241038');
  if (phone.matches) themeMeta.content = getComputedStyle(s).getPropertyValue('--bg').trim();
  s.querySelectorAll('.count').forEach(countUp);
  if (!quiet) { buzz(); if (!document.activeElement || document.activeElement === document.body || document.activeElement.classList.contains('slide')) s.focus({ preventScroll: true }); }
  try { history.replaceState(null, '', '#' + s.dataset.name); } catch (_) {}
}

// tap left half of the card to go back, right half to go forward; swipe works too
let sx = null, sy = null, st = 0;
deck.addEventListener('pointerdown', e => { sx = e.clientX; sy = e.clientY; st = performance.now(); });
deck.addEventListener('pointerup', e => {
  if (sx === null) return;
  const dx = e.clientX - sx, dy = e.clientY - sy; sx = null;
  if (e.target.closest('button, a')) return;
  if (e.target.closest('.spark[data-c]')) return;
  if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) { go(cur + (dx < 0 ? 1 : -1)); return; }
  if (Math.abs(dx) < 8 && Math.abs(dy) < 8 && performance.now() - st < 500) { const r = slides[cur].querySelector('.card').getBoundingClientRect(); go(e.clientX < r.left + r.width / 2 ? cur - 1 : cur + 1); }
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
  b.textContent = all ? 'Show top ' + list.querySelectorAll('.row:not(.extra)').length : 'Show all ' + list.children.length;
  buzz();
}));

// day tooltips
const tip = document.getElementById('tip');
document.querySelectorAll('.dots i[data-tip]').forEach(d => {
  d.addEventListener('pointerenter', e => { if (e.pointerType !== 'mouse') return; const r = d.getBoundingClientRect(); tip.textContent = d.dataset.tip; tip.style.left = (r.left + r.width / 2) + 'px'; tip.style.top = r.top + 'px'; tip.style.opacity = 1; });
  d.addEventListener('pointerleave', () => tip.style.opacity = 0);
});

// day graphs: hover (mouse) or drag (finger) reads one day; at rest the label shows the peak.
// The deck ignores pointerup on a graph, so a scrub never changes slide.
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function dayAt(sp, k, hot) {
  const c = sp._c || (sp._c = sp.dataset.c.split(',').map(Number)), bars = sp.querySelectorAll('i');
  const pk = [...bars].findIndex(b => b.classList.contains('pk'));
  if (k == null) k = pk < 0 ? c.indexOf(Math.max(...c)) : pk;
  let sl = sp.querySelector('.sl');
  if (!sl) { sl = document.createElement('b'); sl.className = 'sl'; sp.appendChild(sl); }
  const d = new Date(+sp.dataset.y, 0, 1 + k), u = sp.dataset.u || 'message';
  sl.textContent = `${MON[d.getMonth()]} ${d.getDate()} · ${c[k].toLocaleString('en-US')} ${c[k] === 1 ? u : u + 's'}`;
  sp.querySelectorAll('i.cur').forEach(b => b.classList.remove('cur'));
  if (hot) bars[k].classList.add('cur');
  sp.classList.toggle('hot', !!hot);
  const w = sl.offsetWidth, x = bars[k].offsetLeft + bars[k].offsetWidth / 2;
  sl.style.transform = `translateX(${Math.max(0, Math.min(sp.clientWidth - w, x - w / 2))}px)`;
}
document.querySelectorAll('.spark[data-c]').forEach(sp => {
  const n = sp.querySelectorAll('i').length;
  const at = e => { const r = sp.getBoundingClientRect(); return Math.max(0, Math.min(n - 1, Math.floor((e.clientX - r.left) / r.width * n))); };
  const rest = () => dayAt(sp);
  sp.addEventListener('pointerdown', e => { if (e.pointerType !== 'mouse') sp.setPointerCapture(e.pointerId); dayAt(sp, at(e), true); });
  sp.addEventListener('pointermove', e => { if (e.pointerType === 'mouse' || sp.hasPointerCapture(e.pointerId)) dayAt(sp, at(e), true); });
  sp.addEventListener('pointerup', e => { if (e.pointerType !== 'mouse') rest(); });
  sp.addEventListener('pointercancel', rest);
  sp.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse') rest(); });
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(rest);
  addEventListener('resize', rest);
});

// summary card tilts toward the pointer
const tilt = document.querySelector('.tilt');
if (tilt && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const card = tilt.querySelector('.card'), sheen = card.querySelector('.sheen');
  tilt.addEventListener('pointermove', e => {
    if (e.pointerType !== 'mouse') return;
    const r = card.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    card.style.transition = 'transform .08s linear';
    card.style.transform = `rotateY(${(x - .5) * 14}deg) rotateX(${(.5 - y) * 14}deg)`;
    sheen.style.setProperty('--mx', x * 100 + '%'); sheen.style.setProperty('--my', y * 100 + '%');
  });
  tilt.addEventListener('pointerleave', () => { card.style.transition = ''; card.style.transform = ''; });
}

// save or share the current slide as a 1080x1920 image; one action, named for what it does here
const actBtns = [...document.querySelectorAll('[data-act]')];
let canShare = false;
try { canShare = !!(navigator.canShare && navigator.canShare({ files: [new File([''], 'x.png', { type: 'image/png' })] })); } catch (_) {}
const ACT = canShare ? 'Share' : 'Save image';
const label = t => actBtns.forEach(b => b.querySelector('.lbl').textContent = t);
const busy = on => actBtns.forEach(b => b.disabled = on);
if (canShare) actBtns.forEach(b => b.querySelector('path').setAttribute('d', 'M12 15V4M8 8l4-4 4 4M6 12v7h12v-7'));
label(ACT);
let ready = null, resetT = 0;
function flash(t, ms) { label(t); clearTimeout(resetT); resetT = setTimeout(() => { label(ACT); busy(false); }, ms || 1800); }
async function render(s) {
  // capture a clone at a fixed 360x640 so every device gets exactly 1080x1920, final frame, no chrome
  const box = document.createElement('section');
  box.className = themeOf(s).join(' ') + ' capturing';
  box.setAttribute('aria-hidden', 'true');
  box.style.cssText = 'position:fixed;left:-10000px;top:0;--cw:360px;--ch:640px';
  const card = s.querySelector('.card').cloneNode(true);
  card.removeAttribute('id'); card.style.transform = 'none'; card.classList.add('saving');
  card.querySelectorAll('.chrome').forEach(n => n.remove());
  box.appendChild(card); document.body.appendChild(box);
  card.querySelectorAll('.count').forEach(c => c.textContent = (c.dataset.fmt === 'dec' ? (+c.dataset.to).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : (+c.dataset.to).toLocaleString('en-US')) + (c.dataset.suffix || ''));
  card.querySelectorAll('.hero.fit, .split b, .grid4 dd, .stats3 dd').forEach(e => fit(e));
  card.querySelectorAll('.spark[data-c]').forEach(sp => dayAt(sp));
  card.querySelectorAll('.hero.name, .hero.diag, .diag-sm').forEach(fitName);
  card.querySelectorAll('.ptitle:not(.poster .ptitle), .stretch span').forEach(e => fit(e, 3));
  try { return await modernScreenshot.domToBlob(card, { scale: 3, width: 360, height: 640 }); }
  finally { box.remove(); }
}
function download(blob, name) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
actBtns.forEach(btn => btn.addEventListener('click', async e => {
  e.stopPropagation();
  const s = slides[cur], name = `${FILE}_${s.dataset.name}.png`;
  if (!window.modernScreenshot) { flash('Offline. Take a screenshot', 2400); return; }
  const held = ready && ready.slide === s ? ready.blob : null; ready = null;
  let blob = held;
  if (!blob) {
    label(canShare ? 'Preparing…' : 'Saving…'); busy(true);
    try { blob = await render(s); } catch (err) { console.error(err); flash('Could not save. Take a screenshot', 2400); return; }
  }
  if (canShare) {
    try {
      await navigator.share({ files: [new File([blob], name, { type: 'image/png' })], text: `My ${document.title} — wrap2026.com` });
      buzz(); label(ACT); busy(false);
    } catch (err) {
      if (err.name === 'AbortError') { label(ACT); busy(false); return; }
      // the share sheet needs a fresh tap after a slow render; keep the image for it
      if (err.name === 'NotAllowedError' && !held) { ready = { slide: s, blob }; label('Tap to share'); busy(false); return; }
      download(blob, name); flash('Saved');
    }
    return;
  }
  download(blob, name); buzz(); flash('Saved');
}));

if (location.search.includes('still')) document.body.classList.add('capturing');
if (auto) {
  document.body.classList.add('auto');
  bars.addEventListener('animationend', e => { if (e.animationName === 'fill') go(cur + 1 < slides.length ? cur + 1 : 0, true); });
  // press and hold pauses, like stories
  deck.addEventListener('pointerdown', () => document.body.classList.add('held'));
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(t => deck.addEventListener(t, () => document.body.classList.remove('held')));
}
const start = slides.findIndex(s => '#' + s.dataset.name === location.hash);
go(start > 0 ? start : 0, true);
})();
</script>
</body></html>'''
