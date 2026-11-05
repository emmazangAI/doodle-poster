// 用 macOS Vision 把照片主体抠成透明 PNG（macOS 14+）
// 用法: cutout <input.jpg|png> <output.png>
import Foundation
import Vision
import CoreImage
import AppKit

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: cutout <in> <out>\n".data(using: .utf8)!)
    exit(1)
}

let handler = VNImageRequestHandler(url: URL(fileURLWithPath: args[1]), options: [:])
let request = VNGenerateForegroundInstanceMaskRequest()

do {
    try handler.perform([request])
} catch {
    FileHandle.standardError.write("vision error: \(error)\n".data(using: .utf8)!)
    exit(2)
}

guard let result = request.results?.first else {
    FileHandle.standardError.write("no foreground instance found\n".data(using: .utf8)!)
    exit(3)
}

do {
    let buffer = try result.generateMaskedImage(ofInstances: result.allInstances,
                                                from: handler,
                                                croppedToInstancesExtent: false)
    let ci = CIImage(cvPixelBuffer: buffer)
    try CIContext().writePNGRepresentation(of: ci,
                                           to: URL(fileURLWithPath: args[2]),
                                           format: .RGBA8,
                                           colorSpace: CGColorSpaceCreateDeviceRGB())
    print("ok")
} catch {
    FileHandle.standardError.write("mask error: \(error)\n".data(using: .utf8)!)
    exit(4)
}
