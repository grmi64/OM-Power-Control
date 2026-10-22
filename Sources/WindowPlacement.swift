import Foundation
import CoreGraphics

// Logical desktop coordinates; the native adapter excludes the Dock/menu bar.
// Same recovery rules as DX Caliber's platform-neutral window_management.js.
struct WindowPlacement {
    static func recover(_ frame: CGRect, screens: [CGRect]) -> CGRect {
        let screens = screens.filter { [$0.minX,$0.minY,$0.width,$0.height].allSatisfy { $0.isFinite } && $0.width > 0 && $0.height > 0 }
        guard var target = screens.first else { return frame }
        let valid = [frame.origin.x,frame.origin.y,frame.width,frame.height].allSatisfy { $0.isFinite } && frame.width > 0 && frame.height > 0
        if valid && screens.contains(where: { $0.contains(frame) }) { return frame }
        var best: CGFloat = 0
        if valid { for screen in screens {
            let area = max(0,min(frame.maxX,screen.maxX)-max(frame.minX,screen.minX)) * max(0,min(frame.maxY,screen.maxY)-max(frame.minY,screen.minY))
            if area > best { best = area; target = screen }
        } }
        let width = min(valid ? frame.width : 800,target.width), height = min(valid ? frame.height : 600,target.height)
        return CGRect(x:max(target.minX,min(valid ? frame.minX : target.midX-width/2,target.maxX-width)),y:max(target.minY,min(valid ? frame.minY : target.midY-height/2,target.maxY-height)),width:width,height:height)
    }
}
