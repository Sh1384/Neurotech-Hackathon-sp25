guard let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back) else { return }

do {
    try device.lockForConfiguration()
    if device.isTorchAvailable && device.isTorchModeSupported(.on) {
        device.torchMode = .on
        try device.setTorchModeOn(level: AVCaptureDevice.maxAvailableTorchLevel)
    }
    device.unlockForConfiguration()
} catch {
    print("Torch configuration error: \(error)")
}

