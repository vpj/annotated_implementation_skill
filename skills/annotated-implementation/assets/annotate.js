// Renders math and makes identifiers and equation symbols clickable in an annotated implementation.
//
// Equation linking: every math expression on the page is tokenized. When a shorter expression
// appears again (on its own, or inside a longer equation), every occurrence is wrapped in
// \htmlClass{eq-k}. Clicking one dims the page and makes every occurrence glow; clicking an
// identifier in the code does the same for that name. This only works when the same symbol is
// written with identical LaTeX throughout the page.
(function () {
    'use strict';

    const CODE_NAMES = '.highlight .n, .highlight .nn, .highlight .nc, .highlight .nf';

    const DELIMITERS = [
        {left: '$$', right: '$$', display: true},
        {left: '\\[', right: '\\]', display: true},
        {left: '\\begin{equation}', right: '\\end{equation}', display: true},
        {left: '\\begin{equation*}', right: '\\end{equation*}', display: true},
        {left: '\\begin{align}', right: '\\end{align}', display: true},
        {left: '\\begin{align*}', right: '\\end{align*}', display: true},
        {left: '\\begin{gather}', right: '\\end{gather}', display: true},
        {left: '\\begin{gather*}', right: '\\end{gather*}', display: true},
        {left: '$', right: '$', display: false},
        {left: '\\(', right: '\\)', display: false},
    ];

    const KATEX_OPTIONS = {
        throwOnError: false,
        strict: 'ignore',
        trust: (ctx) => ctx.command === '\\htmlClass',
        macros: {},
    };

    // Commands whose first brace group is kept together with the command as one token:
    // text-mode arguments and font/environment names must never be split by linking.
    const ATOMIC = new Set([
        '\\begin', '\\end', '\\text', '\\textrm', '\\textit', '\\textbf', '\\textsf', '\\texttt',
        '\\mbox', '\\mathrm', '\\mathbb', '\\mathcal', '\\mathbf', '\\mathit', '\\mathsf', '\\mathtt',
        '\\mathfrak', '\\boldsymbol', '\\operatorname', '\\htmlClass', '\\color', '\\textcolor',
        '\\label', '\\tag', '\\ref', '\\eqref',
    ]);

    // Expressions containing these are never linked: wrapping them in a group would break layout.
    const UNLINKABLE = /^(&|\\\\|\\begin|\\end|\\left|\\right|\\middle|\\tag|\\label|\\nonumber|\\notag|\\hline)/;

    // Single tokens that are never linked on their own: index letters and bare numbers appear in
    // almost every subscript, so linking them colours everything and links nothing meaningful.
    const INDEX_LETTERS = new Set(['i', 'j', 'k', 'l', 'n', 't', 'T', 'd', 'p']);

    function matchBrace(tex, open) {
        let depth = 0;
        for (let i = open; i < tex.length; i++) {
            if (tex[i] === '\\') {
                i++;
            } else if (tex[i] === '{') {
                depth++;
            } else if (tex[i] === '}') {
                depth--;
                if (depth === 0) return i;
            }
        }
        return -1;
    }

    function tokenize(tex) {
        const tokens = [];
        let i = 0;
        while (i < tex.length) {
            const c = tex[i];
            if (/\s/.test(c)) {
                i++;
                continue;
            }
            if (c !== '\\') {
                tokens.push(c);
                i++;
                continue;
            }
            let j = i + 1;
            if (j < tex.length && /[a-zA-Z]/.test(tex[j])) {
                while (j < tex.length && /[a-zA-Z]/.test(tex[j])) j++;
            } else {
                j = Math.min(j + 1, tex.length);
            }
            let token = tex.slice(i, j);
            if (ATOMIC.has(token)) {
                let k = j;
                while (k < tex.length && /\s/.test(tex[k])) k++;
                if (tex[k] === '{') {
                    const close = matchBrace(tex, k);
                    if (close > 0) {
                        token = tex.slice(i, close + 1);
                        j = close + 1;
                    }
                }
            }
            tokens.push(token);
            i = j;
        }
        return tokens;
    }

    function join(tokens) {
        let out = '';
        for (const t of tokens) {
            if (/\\[a-zA-Z]+$/.test(out) && /^[a-zA-Z0-9]/.test(t)) out += ' ';
            out += t;
        }
        return out;
    }

    function isLinkable(tokens) {
        if (tokens.length === 1 && (INDEX_LETTERS.has(tokens[0]) || /^\d+$/.test(tokens[0]))) return false;
        if (tokens.every((t) => /^\d$/.test(t) || t === '.')) return false;
        let depth = 0;
        let hasSymbol = false;
        for (const t of tokens) {
            if (UNLINKABLE.test(t)) return false;
            if (t === '{') depth++;
            if (t === '}') depth--;
            if (depth < 0) return false;
            if (/^[a-zA-Z0-9\\]/.test(t)) hasSymbol = true;
        }
        return depth === 0 && hasSymbol;
    }

    function sameTokens(tokens, at, part) {
        if (at + part.length > tokens.length) return false;
        for (let k = 0; k < part.length; k++) {
            if (tokens[at + k] !== part[k]) return false;
        }
        return true;
    }

    function wrap(part, cls) {
        return ['{', `\\htmlClass{${cls}}`, '{', ...part, '}', '}'];
    }

    // Wrapping `x_t` in `x_t^2` would turn it into `{x_t}^2`, which typesets the superscript
    // after the subscript instead of stacked above it, so such occurrences are left unlinked.
    function breaksScripts(tokens, at, part) {
        const next = tokens[at + part.length];
        return (next === '^' || next === '_') && (part.includes('^') || part.includes('_'));
    }

    // Returns [tokens with every occurrence of `part` wrapped, whether anything was wrapped].
    function linkPart(tokens, part, cls) {
        const out = [];
        let found = false;
        let i = 0;
        while (i < tokens.length) {
            if (sameTokens(tokens, i, part) && !breaksScripts(tokens, i, part)) {
                out.push(...wrap(part, cls));
                i += part.length;
                found = true;
            } else {
                out.push(tokens[i]);
                i++;
            }
        }
        return [out, found];
    }

    // Checked in display mode: environments like align* are only allowed there, and anything valid
    // inline is valid in display mode too.
    function renders(tex) {
        try {
            katex.renderToString(tex, Object.assign({}, KATEX_OPTIONS, {throwOnError: true, displayMode: true}));
            return true;
        } catch (e) {
            return false;
        }
    }

    // Maps each raw math string on the page to its linked version.
    function linkEquations(rawList) {
        const keyOf = new Map();
        const uses = new Map();
        for (const raw of rawList) {
            const key = join(tokenize(raw));
            keyOf.set(raw, key);
            uses.set(key, (uses.get(key) || 0) + 1);
        }

        // Longest first, so shorter expressions are found inside longer ones before they are wrapped.
        const keys = [...uses.keys()].sort((a, b) => b.length - a.length || (a < b ? -1 : 1));
        const tokens = keys.map(tokenize);
        const linkable = tokens.map(isLinkable);
        const reps = keys.map((k) => uses.get(k));
        const result = new Map();

        for (let i = 0; i < keys.length; i++) {
            let eq = tokens[i];
            for (let j = i + 1; j < keys.length; j++) {
                if (!linkable[j]) continue;
                const [linked, found] = linkPart(eq, tokens[j], `eq-${j}`);
                if (found) {
                    eq = linked;
                    reps[j]++;
                }
            }
            if (reps[i] > 1 && linkable[i]) {
                eq = wrap(eq, `eq-${i}`);
            }
            const linked = join(eq);
            result.set(keys[i], linked !== keys[i] && renders(linked) ? linked : keys[i]);
        }

        const byRaw = new Map();
        for (const raw of rawList) byRaw.set(raw, result.get(keyOf.get(raw)));
        return byRaw;
    }

    // The transform from an element's own coordinates to its <svg>'s user (viewBox) coordinates,
    // from the `transform` attributes of the element and its ancestors. Needs no layout.
    function svgMatrix(el, svg) {
        let m = svg.createSVGMatrix();
        for (let e = el; e && e !== svg; e = e.parentNode) {
            const t = e.transform && e.transform.baseVal.consolidate();
            if (t) m = t.matrix.multiply(m);
        }
        return m;
    }

    // KaTeX output is HTML, so it cannot go inside an SVG <text>. A <foreignObject> is not the
    // answer either: WebKit (Safari) lays out positioned content inside one without the
    // foreignObject's offset or the SVG's scaling, and KaTeX is built from positioned boxes, so the
    // math lands far from where it belongs. Instead, each <text> containing `$` is moved out of the
    // SVG into an HTML overlay on top of it. The label sits at the text's anchor point in percent of
    // the viewBox, honours text-anchor, rotation, font size, weight, fill and opacity, and is sized in
    // container units, so it moves and scales with the drawing at any width.
    function svgMathLabels(root) {
        for (const svg of root.querySelectorAll('figure svg')) {
            const texts = [...svg.querySelectorAll('text')].filter((t) => t.textContent.includes('$'));
            const box = svg.viewBox && svg.viewBox.baseVal;
            if (!texts.length || !box || !box.width) continue;

            const frame = document.createElement('div');
            frame.className = 'svg-frame';
            const width = svg.getAttribute('width') || '100%';
            frame.style.width = /^[\d.]+$/.test(width) ? `${width}px` : width;
            svg.replaceWith(frame);
            frame.appendChild(svg);
            svg.setAttribute('width', '100%');
            const overlay = document.createElement('div');
            overlay.className = 'svg-labels';
            frame.appendChild(overlay);

            for (const text of texts) {
                const style = getComputedStyle(text);
                const m = svgMatrix(text, svg);
                const p = svg.createSVGPoint();
                p.x = parseFloat(text.getAttribute('x') || '0');
                p.y = parseFloat(text.getAttribute('y') || '0');
                const at = p.matrixTransform(m);
                const angle = Math.atan2(m.b, m.a) * 180 / Math.PI;
                const shift = {middle: '-50%', end: '-100%'}[style.textAnchor] || '0';

                const label = document.createElement('div');
                label.className = 'svg-label';
                label.style.left = `${(at.x - box.x) / box.width * 100}%`;
                label.style.top = `${(at.y - box.y) / box.height * 100}%`;
                label.style.fontSize = `calc(${parseFloat(style.fontSize) / box.width} * 100cqw)`;
                label.style.transform = `rotate(${angle}deg) translate(${shift}, calc(-50% - 0.35em))`;
                label.style.fontWeight = style.fontWeight;
                label.style.opacity = style.opacity;
                if (style.fill && style.fill.startsWith('rgb')) label.style.color = style.fill;
                label.textContent = text.textContent;
                overlay.appendChild(label);
                text.remove();
            }
        }
    }

    // Diagram labels whose typeset math is not where the label is, or labels that stick out of their
    // diagram. Either means the drawing is broken in this browser or the label is placed off the
    // figure; both look wrong to the reader even when every equation rendered.
    function misplacedSvgLabels(root) {
        const found = [];
        const outside = (inner, outer, slack) => inner.width > 0 && (inner.left < outer.left - slack
            || inner.right > outer.right + slack || inner.top < outer.top - slack || inner.bottom > outer.bottom + slack);
        for (const label of root.querySelectorAll('.svg-label')) {
            if (label.offsetParent === null) continue;
            const rect = label.getBoundingClientRect();
            const em = parseFloat(getComputedStyle(label).fontSize);
            const frame = label.closest('.svg-frame').getBoundingClientRect();
            const strayMath = [...label.querySelectorAll('.katex-html')].some((k) => outside(k.getBoundingClientRect(), rect, em));
            if (strayMath || outside(rect, frame, 2)) {
                found.push({section: sectionId(label), text: label.textContent.trim().slice(0, 40),
                    problem: strayMath ? 'math drawn away from its label' : 'label outside its diagram'});
            }
        }
        return found;
    }

    // SVG labels that look like math but are plain text: LaTeX syntax outside `$...$`, or Unicode
    // sub/superscripts standing in for it. Both render badly; write the label as `$...$` instead.
    function plainMathInSvg(root) {
        const looksLikeMath = /[_^\\][{\w]|[₀-ₜᵢ-ᵪ⁰-ⁿ]/;
        return [...root.querySelectorAll('svg text')]
            .filter((t) => looksLikeMath.test(t.textContent))
            .map((t) => ({section: sectionId(t), text: t.textContent}));
    }

    // Diagram text that is hard to read against the page in the current colour scheme, typically an
    // SVG <text> or label with a hard-coded dark fill shown in dark mode (or a light one in light mode).
    function lowContrastSvgText(root) {
        const rgb = (c) => (c.match(/[\d.]+/g) || []).slice(0, 4).map(Number);
        const opaque = (c) => c && c !== 'transparent' && !(rgb(c).length === 4 && rgb(c)[3] === 0);
        const luminance = ([r, g, b]) => {
            const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
            return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
        };
        const background = (el) => {
            for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
                const c = getComputedStyle(e).backgroundColor;
                if (opaque(c)) return rgb(c);
            }
            return [255, 255, 255];
        };
        const found = [];
        for (const el of root.querySelectorAll('figure svg text, figure .svg-label')) {
            const style = getComputedStyle(el);
            const colour = el.tagName.toLowerCase() === 'text' ? style.fill : style.color;
            if (!colour || !colour.startsWith('rgb')) continue;
            const [a, b] = [luminance(rgb(colour)), luminance(background(el))];
            const contrast = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
            if (contrast < 3) found.push({section: sectionId(el), text: el.textContent.trim().slice(0, 40), contrast: +contrast.toFixed(2)});
        }
        return found;
    }

    function renderMath(root) {
        const base = {delimiters: DELIMITERS, ignoredClasses: ['no-math'], ...KATEX_OPTIONS};

        // Pass 1: collect every math string by rendering a throwaway copy.
        const collected = [];
        renderMathInElement(root.cloneNode(true), {
            ...base,
            preProcess: (math) => {
                collected.push(math);
                return '';
            },
        });

        // Pass 2: render the real page with linked equations.
        const linked = linkEquations(collected);
        renderMathInElement(root, {...base, preProcess: (math) => linked.get(math) ?? math});
    }

    function eqClass(el) {
        for (const c of el.classList) {
            if (/^eq-\d+$/.test(c)) return c;
        }
        return null;
    }

    // The group a clicked element belongs to: an identifier's name in the code, or the innermost
    // linked expression in an equation.
    function clickGroup(target, root) {
        const name = target.closest(CODE_NAMES);
        if (name && root.contains(name)) {
            const text = name.textContent;
            return {key: 'code:' + text, members: () => [...root.querySelectorAll(CODE_NAMES)].filter((e) => e.textContent === text)};
        }
        let el = target;
        while (el && el !== root && !(el.classList && eqClass(el))) el = el.parentElement;
        if (el && el !== root && el.closest('.katex')) {
            const cls = eqClass(el);
            return {key: 'eq:' + cls, members: () => [...root.querySelectorAll('.' + cls)]};
        }
        return null;
    }

    // Clicking an identifier or a linked symbol dims the page and makes every occurrence glow;
    // clicking it again, or pressing Escape, turns the lights back on.
    function setupClickHighlight(root) {
        let active = null;
        const clear = () => {
            if (!active) return;
            active.elements.forEach((e) => e.classList.remove('clicked'));
            document.body.classList.remove('lights-off');
            active = null;
        };
        root.addEventListener('click', (event) => {
            const group = clickGroup(event.target, root);
            if (!group) return;
            event.preventDefault();
            const same = active && active.key === group.key;
            clear();
            if (same) return;
            active = {key: group.key, elements: group.members()};
            active.elements.forEach((e) => e.classList.add('clicked'));
            document.body.classList.add('lights-off');
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') clear();
        });
    }

    function sectionId(el) {
        const section = el.closest('.section');
        return section ? section.id || 'header' : null;
    }

    // Visible prose that still contains `$` after rendering: math that was not picked up.
    function unrenderedDollars(root) {
        const found = [];
        root.querySelectorAll('.docs').forEach((docs) => {
            const copy = docs.cloneNode(true);
            copy.querySelectorAll('.katex, .no-math, code, pre, script, style').forEach((e) => e.remove());
            const text = copy.textContent;
            const at = text.indexOf('$');
            if (at >= 0) found.push({section: sectionId(docs), text: text.slice(Math.max(0, at - 40), at + 40).trim()});
        });
        return found;
    }

    // Publishes `window.annotationReport` and shows a banner if anything needs fixing.
    function selfCheck(root) {
        const annotation = (el) => {
            const a = el.querySelector('annotation');
            return a ? a.textContent : el.textContent;
        };
        const mathErrors = [...root.querySelectorAll('.katex-error')].map((e) => ({
            tex: e.textContent, message: e.getAttribute('title')}));
        const closed = [...root.querySelectorAll('details:not([open])')];
        closed.forEach((d) => { d.open = true; });
        const overflowing = [...root.querySelectorAll('.katex-display')]
            .filter((e) => e.offsetParent !== null && e.scrollWidth > e.clientWidth + 1)
            .map((e) => ({section: sectionId(e), tex: annotation(e)}));
        closed.forEach((d) => { d.open = false; });
        const unrenderedDollar = unrenderedDollars(root);
        const svgPlainMath = plainMathInSvg(root);
        const svgLowContrast = lowContrastSvgText(root);
        const svgMisplaced = misplacedSvgLabels(root);
        const report = {mathErrors, overflowing, unrenderedDollar, svgPlainMath, svgLowContrast, svgMisplaced,
            ok: !mathErrors.length && !overflowing.length && !unrenderedDollar.length && !svgPlainMath.length
                && !svgLowContrast.length && !svgMisplaced.length};
        window.annotationReport = report;
        if (report.ok) return;

        mathErrors.forEach((e) => console.error('KaTeX error:', e.message, '\n', e.tex));
        overflowing.forEach((e) => console.warn(`Equation wider than its column in #${e.section}:`, e.tex));
        unrenderedDollar.forEach((e) => console.warn(`Unrendered $ in #${e.section}:`, e.text));
        svgPlainMath.forEach((e) => console.warn(`Diagram label in #${e.section} looks like math but is not in $...$:`, e.text));
        svgLowContrast.forEach((e) => console.warn(`Diagram text in #${e.section} has contrast ${e.contrast}:1 against the page:`, e.text));
        svgMisplaced.forEach((e) => console.warn(`Diagram label in #${e.section}: ${e.problem}:`, e.text));
        const parts = [];
        if (mathErrors.length) parts.push(`${mathErrors.length} math error(s)`);
        if (overflowing.length) parts.push(`${overflowing.length} equation(s) too wide`);
        if (unrenderedDollar.length) parts.push(`${unrenderedDollar.length} unrendered $`);
        if (svgPlainMath.length) parts.push(`${svgPlainMath.length} diagram label(s) with plain-text math`);
        if (svgLowContrast.length) parts.push(`${svgLowContrast.length} diagram label(s) hard to read in this colour scheme`);
        if (svgMisplaced.length) parts.push(`${svgMisplaced.length} diagram label(s) out of place`);
        const banner = document.createElement('div');
        banner.className = 'math-errors';
        banner.textContent = `${parts.join(', ')} - see console or window.annotationReport`;
        document.body.appendChild(banner);
    }

    // Rendering math changes the page height, so the browser's jump to `#anchor` on load lands in the
    // wrong place. Jump again once the layout is final.
    function scrollToHash() {
        const id = decodeURIComponent(location.hash.slice(1));
        const target = id && document.getElementById(id);
        if (target) {
            target.scrollIntoView();
        }
    }

    function main() {
        const root = document.querySelector('.page');
        setupClickHighlight(root);
        if (typeof renderMathInElement === 'undefined') {
            console.error('KaTeX did not load; math is not rendered');
            window.annotationReport = {ok: false, error: 'KaTeX did not load'};
            return;
        }
        svgMathLabels(root);
        renderMath(root);
        scrollToHash();
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(() => {
                scrollToHash();
                selfCheck(root);
            });
        } else {
            selfCheck(root);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', main);
    } else {
        main();
    }
})();
