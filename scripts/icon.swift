import Cocoa
let out=CommandLine.arguments[1]
let image=NSImage(size:NSSize(width:1024,height:1024))
image.lockFocus()
NSColor.clear.setFill();NSRect(x:0,y:0,width:1024,height:1024).fill()
let shell=NSBezierPath(roundedRect:NSRect(x:70,y:70,width:884,height:884),xRadius:190,yRadius:190)
NSColor(calibratedRed:0.12,green:0.16,blue:0.18,alpha:1).setFill();shell.fill()
NSColor(calibratedWhite:0.45,alpha:1).setStroke();shell.lineWidth=12;shell.stroke()
let face=NSBezierPath(roundedRect:NSRect(x:125,y:185,width:774,height:640),xRadius:65,yRadius:65)
NSColor(calibratedRed:0.035,green:0.065,blue:0.075,alpha:1).setFill();face.fill()
let amber=NSColor(calibratedRed:0.95,green:0.71,blue:0.35,alpha:1)
func text(_ s:String,_ size:CGFloat,_ x:CGFloat,_ y:CGFloat,_ color:NSColor){s.draw(at:NSPoint(x:x,y:y),withAttributes:[.font:NSFont.monospacedDigitSystemFont(ofSize:size,weight:.bold),.foregroundColor:color])}
text("OM",180,335,555,amber);text("3501A",77,355,470,NSColor(calibratedWhite:0.8,alpha:1))
for i in 0..<15 { let rect=NSRect(x:180+CGFloat(i)*45,y:350,width:30,height:64);(i<11 ? amber:NSColor(calibratedWhite:0.2,alpha:1)).setFill();NSBezierPath(roundedRect:rect,xRadius:7,yRadius:7).fill() }
let wave=NSBezierPath();wave.move(to:NSPoint(x:185,y:265))
for x in stride(from:185.0,through:840.0,by:2){wave.line(to:NSPoint(x:x,y:265+sin((x-185)/26)*25))};amber.setStroke();wave.lineWidth=9;wave.stroke()
image.unlockFocus()
let rep=NSBitmapImageRep(data:image.tiffRepresentation!)!
try! rep.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:out))
