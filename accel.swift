import UIKit
import CoreMotion
import Accelerate // For variance calculation

class FidgetDetectionViewController: UIViewController {

    let motionManager = CMMotionManager()
    var accelerometerDataBuffer: [CMAccelerometerData] = []
    let windowSize = 50 // Number of data points in a window (e.g., 1 second at 50 Hz)
    let fidgetThreshold: Double = 0.05 // Example threshold - needs tuning

    override func viewDidLoad() {
        super.viewDidLoad()
        startAccelerometerUpdates()
    }

    func startAccelerometerUpdates() {
        if motionManager.isAccelerometerAvailable {
            motionManager.accelerometerUpdateInterval = 0.02
            motionManager.startAccelerometerUpdates(to: OperationQueue.main) { (data, error) in
                if let accelerometerData = data {
                    self.accelerometerDataBuffer.append(accelerometerData)
                    if self.accelerometerDataBuffer.count >= self.windowSize {
                        self.analyzeForFidgeting()
                        self.accelerometerDataBuffer.removeFirst(self.windowSize - 1) // Overlapping windows
                    }
                }
                if let error = error {
                    print("Error getting accelerometer data: \(error.localizedDescription)")
                }
            }
        } else {
            print("Accelerometer is not available.")
        }
    }

    func analyzeForFidgeting() {
        let magnitudes = accelerometerDataBuffer.map {
            sqrt($0.acceleration.x * $0.acceleration.x +
                 $0.acceleration.y * $0.acceleration.y +
                 $0.acceleration.z * $0.acceleration.z)
        }

        if magnitudes.count > 1 {
            var mean = 0.0
            for magnitude in magnitudes {
                mean += magnitude
            }
            mean /= Double(magnitudes.count)

            var variance = 0.0
            for magnitude in magnitudes {
                variance += pow(magnitude - mean, 2)
            }
            variance /= Double(magnitudes.count - 1) // Sample variance

            print("Variance of magnitude: \(variance)")

            if variance > fidgetThreshold {
                print("Fidgeting detected!")
                // Potentially trigger some action in your accessibility app
            }
        }
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        motionManager.stopAccelerometerUpdates()
    }
}