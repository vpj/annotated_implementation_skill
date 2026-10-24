// Renders math and makes identifiers and equation symbols clickable on an annotated implementation page.
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

    const SVG_NS = 'http://www.w3.org/2000/svg';

    // KaTeX output is HTML, which cannot live inside an SVG <text>. Every <text> whose content
    // contains `$` is replaced by a <foreignObject> anchored at the same point (honouring
    // text-anchor, font size, weight and fill) holding an HTML label, which renderMath then typesets.
    // The label scales with the SVG's viewBox like the text it replaces.
    function svgMathLabels(root) {
        for (const text of root.querySelectorAll('svg text')) {
            if (!text.textContent.includes('$')) continue;
            const svg = text.ownerSVGElement;
            const box = svg.viewBox && svg.viewBox.baseVal;
            const width = box && box.width ? box.width : svg.getBoundingClientRect().width;
            const x = parseFloat(text.getAttribute('x') || '0');
            const y = parseFloat(text.getAttribute('y') || '0');
            const style = getComputedStyle(text);
            const size = parseFloat(style.fontSize);
            const anchor = style.textAnchor;
            const half = Math.max(Math.min(x, width - x), size);
            const [left, span, justify] = anchor === 'middle' ? [x - half, 2 * half, 'center']
                : anchor === 'end' ? [x - Math.max(x, size), Math.max(x, size), 'flex-end']
                : [x, Math.max(width - x, size), 'flex-start'];

            const fo = document.createElementNS(SVG_NS, 'foreignObject');
            fo.setAttribute('x', left);
            fo.setAttribute('y', y - 1.85 * size);
            fo.setAttribute('width', span);
            fo.setAttribute('height', 3 * size);
            fo.setAttribute('class', 'svg-math');
            if (text.hasAttribute('transform')) fo.setAttribute('transform', text.getAttribute('transform'));
            const label = document.createElement('div');
            label.className = 'svg-label';
            label.style.fontSize = `${size}px`;
            label.style.fontWeight = style.fontWeight;
            label.style.justifyContent = justify;
            if (style.fill && style.fill !== 'none') label.style.color = style.fill;
            const line = document.createElement('span');
            line.textContent = text.textContent;
            label.appendChild(line);
            fo.appendChild(label);
            text.replaceWith(fo);
        }
    }

    // SVG labels that look like math but are plain text: LaTeX syntax outside `$...$`, or Unicode
    // sub/superscripts standing in for it. Both render badly; write the label as `$...$` instead.
    function plainMathInSvg(root) {
        const looksLikeMath = /[_^\\][{\w]|[₀-ₜᵢ-ᵪ⁰-ⁿ]/;
        return [...root.querySelectorAll('svg text')]
            .filter((t) => looksLikeMath.test(t.textContent))
            .map((t) => ({section: sectionId(t), text: t.textContent}));
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
        const report = {mathErrors, overflowing, unrenderedDollar, svgPlainMath,
            ok: !mathErrors.length && !overflowing.length && !unrenderedDollar.length && !svgPlainMath.length};
        window.annotationReport = report;
        if (report.ok) return;

        mathErrors.forEach((e) => console.error('KaTeX error:', e.message, '\n', e.tex));
        overflowing.forEach((e) => console.warn(`Equation wider than its column in #${e.section}:`, e.tex));
        unrenderedDollar.forEach((e) => console.warn(`Unrendered $ in #${e.section}:`, e.text));
        svgPlainMath.forEach((e) => console.warn(`Diagram label in #${e.section} looks like math but is not in $...$:`, e.text));
        const parts = [];
        if (mathErrors.length) parts.push(`${mathErrors.length} math error(s)`);
        if (overflowing.length) parts.push(`${overflowing.length} equation(s) too wide`);
        if (unrenderedDollar.length) parts.push(`${unrenderedDollar.length} unrendered $`);
        if (svgPlainMath.length) parts.push(`${svgPlainMath.length} diagram label(s) with plain-text math`);
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
