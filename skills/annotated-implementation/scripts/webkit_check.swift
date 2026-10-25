// Load an annotated page in WebKit (the engine behind Safari), print its self-check report, and save
// a PNG of every <figure> so diagrams can be inspected. Chrome-based previews do not show WebKit-only
// layout bugs, so run this on macOS for every page with a diagram.
//
// Usage:
//   swift webkit_check.swift <url> <out-dir> [light|dark] [width]
//
// Prints the page's `window.annotationReport` as JSON and the path of each figure snapshot.
// Exits 1 if the report is not ok.

import AppKit
import WebKit

let args = CommandLine.arguments
guard args.count >= 3, let url = URL(string: args[1]) else {
    print("usage: swift webkit_check.swift <url> <out-dir> [light|dark] [width]")
    exit(2)
}
let outDir = URL(fileURLWithPath: args[2])
let dark = args.count > 3 && args[3] == "dark"
let width = args.count > 4 ? Double(args[4]) ?? 1400 : 1400
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)

final class Checker: NSObject, WKNavigationDelegate {
    let view = WKWebView(frame: NSRect(x: 0, y: 0, width: width, height: 900))
    var reportOk = false

    override init() {
        super.init()
        view.navigationDelegate = self
        view.appearance = NSAppearance(named: dark ? .darkAqua : .aqua)
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { self.report() }
    }

    func report() {
        let js = """
        (() => {
            document.querySelectorAll('figure').forEach((f, i) => { if (!f.id) f.id = 'webkit-figure-' + i; });
            return JSON.stringify({report: window.annotationReport || null,
                                   figures: [...document.querySelectorAll('figure')].map((f) => f.id)});
        })()
        """
        view.evaluateJavaScript(js) { result, error in
            guard let text = result as? String, let data = text.data(using: .utf8),
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                print("could not read the page: \(String(describing: error))")
                exit(2)
            }
            let report = json["report"] as? [String: Any]
            let reportData = try? JSONSerialization.data(withJSONObject: report ?? [:], options: [.sortedKeys])
            print("report: \(reportData.flatMap { String(data: $0, encoding: .utf8) } ?? "missing")")
            self.reportOk = (report?["ok"] as? Bool) ?? false
            self.snapshot(json["figures"] as? [String] ?? [], 0)
        }
    }

    func snapshot(_ ids: [String], _ i: Int) {
        guard i < ids.count else { exit(reportOk ? 0 : 1) }
        let id = ids[i]
        let js = "(() => { const e = document.getElementById('\(id)'); e.scrollIntoView({block: 'start'});"
            + " const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, Math.min(r.height, 900)]; })()"
        view.evaluateJavaScript(js) { result, _ in
            guard let r = result as? [Double] else { self.snapshot(ids, i + 1); return }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                let config = WKSnapshotConfiguration()
                config.rect = NSRect(x: r[0], y: r[1], width: r[2], height: r[3])
                self.view.takeSnapshot(with: config) { image, _ in
                    if let image = image, let tiff = image.tiffRepresentation,
                       let png = NSBitmapImageRep(data: tiff)?.representation(using: .png, properties: [:]) {
                        let path = outDir.appendingPathComponent("\(id)-\(dark ? "dark" : "light").png")
                        try? png.write(to: path)
                        print("figure: \(path.path)")
                    }
                    self.snapshot(ids, i + 1)
                }
            }
        }
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.prohibited)
app.appearance = NSAppearance(named: dark ? .darkAqua : .aqua)
let checker = Checker()
checker.view.load(URLRequest(url: url))
DispatchQueue.main.asyncAfter(deadline: .now() + 60) {
    print("timed out")
    exit(2)
}
app.run()
