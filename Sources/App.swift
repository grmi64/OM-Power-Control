import Cocoa
import WebKit
import Darwin

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate, WKScriptMessageHandler, WKUIDelegate, WKNavigationDelegate {
    var window: NSWindow!
    var web: WKWebView!
    var process: Process?
    var output = Data()
    var lockFD: Int32 = -1
    var shuttingDown = false
    var fullFrame: NSRect?
    var compact = false
    func applicationDidFinishLaunching(_ notification: Notification) {
        // A second launch activates the first app and never opens the USB port.
        let identifier = Bundle.main.bundleIdentifier ?? "com.grmi64.OM3501AControl"
        if let existing = NSRunningApplication.runningApplications(withBundleIdentifier: identifier).first(where: { $0.processIdentifier != ProcessInfo.processInfo.processIdentifier }) {
            existing.activate(options: [.activateAllWindows, .activateIgnoringOtherApps])
            NSApp.terminate(nil)
            return
        }
        let lockDirectory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent(identifier)
        try? FileManager.default.createDirectory(at: lockDirectory, withIntermediateDirectories: true)
        lockFD = Darwin.open(lockDirectory.appendingPathComponent("instance.lock").path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
        guard lockFD >= 0, flock(lockFD, LOCK_EX | LOCK_NB) == 0 else { NSApp.terminate(nil); return }
        configureMenus()
        window = NSWindow(contentRect: NSRect(x: 0,y: 0,width: 900,height: 900), styleMask: [.titled,.closable,.miniaturizable,.resizable], backing: .buffered, defer: false)
        window.title = "OM Power Control"
        window.minSize = NSSize(width: 620,height: 620)
        window.center(); window.delegate = self
        window.setFrameAutosaveName("OM3501AMainWindow")
        ensureWindowVisible()
        NotificationCenter.default.addObserver(self, selector: #selector(recoverForScreenChange(_:)), name: NSApplication.didChangeScreenParametersNotification, object: nil)
        let config = WKWebViewConfiguration()
        config.userContentController.add(self, name: "displayWindow")
        let savedCompact=UserDefaults.standard.bool(forKey:"OMCompact")
        let savedTop=UserDefaults.standard.bool(forKey:"OMOnTop")
        config.userContentController.addUserScript(WKUserScript(source:"window.omPreferences={compact:\(savedCompact),alwaysOnTop:\(savedTop)};",injectionTime:.atDocumentStart,forMainFrameOnly:true))
        let webData = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent(identifier)
        try? FileManager.default.createDirectory(at: webData, withIntermediateDirectories: true)
        web = WKWebView(frame: window.contentView!.bounds, configuration: config)
        web.uiDelegate = self; web.navigationDelegate = self
        web.autoresizingMask = [.width,.height]; window.contentView!.addSubview(web)
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        launchReader()
    }
    func configureMenus() {
        let menu = NSMenu()
        let appMenu = NSMenu()
        let about = appMenu.addItem(withTitle: "About OM Power Control…", action: #selector(showAbout(_:)), keyEquivalent: "")
        about.target = self
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit OM Power Control", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        let item = NSMenuItem(); item.submenu = appMenu; menu.addItem(item)
        let edit = NSMenu(title:"Edit")
        for (title,selector,key) in [("Cut","cut:","x"),("Copy","copy:","c"),("Paste","paste:","v"),("Select All","selectAll:","a")] { edit.addItem(withTitle:title,action:NSSelectorFromString(selector),keyEquivalent:key) }
        let editItem=NSMenuItem(title:"Edit",action:nil,keyEquivalent:""); editItem.submenu=edit; menu.addItem(editItem)
        NSApp.mainMenu = menu
    }
    @objc func showAbout(_ sender: Any?) {
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "Unknown"
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "Unknown"
        NSApp.orderFrontStandardAboutPanel(options: [
            .applicationName: "OM Power Control",
            .applicationVersion: version,
            .version: "Build " + build,
            .credits: NSAttributedString(string: "Created by NY6C\nIndependent, open-source amplifier control."),
            .init(rawValue: "Copyright"): "© 2026 NY6C"
        ])
        NSApp.activate(ignoringOtherApps: true)
    }
    func launchReader() {
        guard let resources = Bundle.main.resourceURL else { return }
        let task = Process(); task.executableURL = resources.appendingPathComponent("amp-engine/amp-engine")
        let args = ["--port","0"]
        task.arguments = args
        task.environment = ProcessInfo.processInfo.environment.merging(["PYTHONDONTWRITEBYTECODE":"1","PYTHONUNBUFFERED":"1"]) { _,new in new }
        let pipe = Pipe(); task.standardOutput = pipe
        task.standardError = FileHandle.standardError
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else { return }
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.output.append(data)
                if let text = String(data:self.output,encoding:.utf8), let line = text.components(separatedBy:"\n").first, let range = line.range(of:"http://127.0.0.1:"), let url = URL(string:String(line[range.lowerBound...]).components(separatedBy:" ")[0]) {
                    self.web.load(URLRequest(url:url))
                    pipe.fileHandleForReading.readabilityHandler = nil
                }
            }
        }
        task.terminationHandler = { [weak self] p in
            if p.terminationStatus != 0 {
                DispatchQueue.main.async { guard let self = self, !self.shuttingDown else { return }; self.showError("The amplifier service stopped. Close any other OM Power Control instance and try again.") }
            }
        }
        do { try task.run(); process = task }
        catch { showError("Could not start amplifier service: \(error.localizedDescription)") }
    }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == "displayWindow", let options = message.body as? [String:Any],
              let small = options["compact"] as? Bool, let onTop = options["alwaysOnTop"] as? Bool else { return }
        UserDefaults.standard.set(small,forKey:"OMCompact")
        UserDefaults.standard.set(onTop,forKey:"OMOnTop")
        window.level = onTop ? .floating : .normal
        window.title = "OM Power Control" + (small ? " · Compact" : "") + (onTop ? " · On top" : "")
        if small != compact {
            if small {
                if window.frame.height >= 650 {
                    fullFrame = window.frame
                    UserDefaults.standard.set(NSStringFromRect(window.frame), forKey: "OM3501AFullFrame")
                } else if let stored = UserDefaults.standard.string(forKey: "OM3501AFullFrame") {
                    fullFrame = NSRectFromString(stored)
                }
                window.minSize = NSSize(width: 380, height: 680)
                window.setContentSize(NSSize(width: 400, height: 690))
            } else {
                window.minSize = NSSize(width: 650, height: 650)
                if let frame = fullFrame { window.setFrame(frame, display: true) }
                else { window.setContentSize(NSSize(width: 900, height: 900)) }
            }
            compact = small
            ensureWindowVisible()
        }
    }
    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let alert = NSAlert(); alert.messageText = "OM Power Control"; alert.informativeText = message
        alert.addButton(withTitle:"Confirm"); alert.addButton(withTitle:"Cancel")
        alert.beginSheetModal(for:window) { completionHandler($0 == .alertFirstButtonReturn) }
    }
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let url = navigationAction.request.url
        decisionHandler(url?.host == "127.0.0.1" ? .allow : .cancel)
    }
    func ensureWindowVisible() {
        guard let window = window, !window.styleMask.contains(.fullScreen) else { return }
        let old = window.frame
        let frame = WindowPlacement.recover(old, screens: NSScreen.screens.map { $0.visibleFrame })
        if frame != old {
            window.minSize = NSSize(width:min(window.minSize.width,frame.width),height:min(window.minSize.height,frame.height))
            window.setFrame(frame, display:true)
        }
    }
    @objc func recoverForScreenChange(_ notification: Notification) { ensureWindowVisible() }
    func applicationDidBecomeActive(_ notification: Notification) { ensureWindowVisible() }
    func showError(_ message:String) {
        let alert=NSAlert();alert.messageText="OM Power Control";alert.informativeText=message
        ensureWindowVisible()
        if let window = window, window.isVisible { alert.beginSheetModal(for:window) }
        else { alert.runModal() }
    }
    func applicationShouldHandleReopen(_ sender:NSApplication,hasVisibleWindows flag:Bool)->Bool { ensureWindowVisible();window?.makeKeyAndOrderFront(nil);return true }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender:NSApplication)->Bool { true }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard !shuttingDown else { return .terminateLater }
        shuttingDown = true
        guard let p = process, p.isRunning else { return .terminateNow }
        p.terminationHandler = nil
        p.terminate()
        DispatchQueue.global(qos: .utility).async {
            let deadline = Date().addingTimeInterval(5)
            while p.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.05) }
            if p.isRunning { Darwin.kill(p.processIdentifier, SIGKILL) }
            DispatchQueue.main.async { sender.reply(toApplicationShouldTerminate: true) }
        }
        return .terminateLater
    }
}
@main
struct InstrumentApplication {
    static func main() {
        let app=NSApplication.shared
        let delegate=AppDelegate()
        app.delegate=delegate
        app.setActivationPolicy(.regular)
        app.run()
    }
}
