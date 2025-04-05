import UIKit

// Data structure to hold metrics
struct TypingBehaviorMetrics {
    var touchForce: Double = 0.0
    var touchDuration: TimeInterval = 0.0
    var errorCount: Int = 0
    var responseLatency: TimeInterval = 0.0
    var typingSpeed: Double = 0.0
}

class TouchMonitorViewController: UIViewController, UITextFieldDelegate {
    
    // MARK: - Properties
    private var metrics = TypingBehaviorMetrics()
    private var touchStartTime: Date?
    private var lastInputTime: Date?
    private var totalCharacters = 0
    private let textField = UITextField()
    
    // Stress thresholds (calibrate through research)
    private let STRESS_FORCE_THRESHOLD = 0.7  // Normalized force
    private let STRESS_ERROR_THRESHOLD = 0.3  // Error rate (errors/chars)
    
    // MARK: - View Lifecycle
    override func viewDidLoad() {
        super.viewDidLoad()
        setupTextField()
    }
    
    private func setupTextField() {
        textField.borderStyle = .roundedRect
        textField.placeholder = "Type here..."
        textField.delegate = self
        textField.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(textField)
        
        NSLayoutConstraint.activate([
            textField.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            textField.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            textField.widthAnchor.constraint(equalTo: view.widthAnchor, multiplier: 0.8)
        ])
    }
    
    // MARK: - Touch Tracking
    override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent?) {
        super.touchesBegan(touches, with: event)
        guard let touch = touches.first else { return }
        
        // Track initial touch time
        touchStartTime = Date()
        
        // Calculate normalized touch force (0-1)
        if traitCollection.forceTouchCapability == .available {
            let force = touch.force / touch.maximumPossibleForce
            metrics.touchForce = max(metrics.touchForce, Double(force))
        }
    }
    
    override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent?) {
        super.touchesEnded(touches, with: event)
        
        // Calculate touch duration
        if let start = touchStartTime {
            metrics.touchDuration += Date().timeIntervalSince(start)
        }
        touchStartTime = nil
    }
    
    // MARK: - Text Analysis
    func textField(_ textField: UITextField, 
                   shouldChangeCharactersIn range: NSRange,
                   replacementString string: String) -> Bool {
        
        // Track response latency (time from touch to input)
        if let lastTouch = touchStartTime {
            metrics.responseLatency = Date().timeIntervalSince(lastTouch)
        }
        
        // Track deletions as potential errors
        if string.isEmpty {
            metrics.errorCount += 1
        } else {
            totalCharacters += 1
        }
        
        // Calculate real-time typing speed
        updateTypingSpeed()
        
        return true
    }
    
    private func updateTypingSpeed() {
        guard let start = lastInputTime else {
            lastInputTime = Date()
            return
        }
        
        let timeInterval = Date().timeIntervalSince(start)
        metrics.typingSpeed = Double(totalCharacters) / timeInterval
        lastInputTime = Date()
    }
    
    // MARK: - Stress Calculation
    func calculateStressProbability() -> Double {
        var stressScore = 0.0
        
        // Force component
        if metrics.touchForce > STRESS_FORCE_THRESHOLD {
            stressScore += 0.4
        }
        
        // Error rate component
        let errorRate = totalCharacters > 0 ? 
            Double(metrics.errorCount) / Double(totalCharacters) : 0.0
        if errorRate > STRESS_ERROR_THRESHOLD {
            stressScore += 0.4
        }
        
        // Duration component (normalized to 10s max)
        stressScore += min(metrics.touchDuration / 10.0, 0.2)
        
        return min(stressScore, 1.0)
    }
    
    // MARK: - Usage Example
    func startMonitoring() {
        textField.becomeFirstResponder()
    }
    
    func stopMonitoring() {
        textField.resignFirstResponder()
        print("""
        Final Metrics:
        - Average Force: \(metrics.touchForce)
        - Total Errors: \(metrics.errorCount)
        - Response Latency: \(metrics.responseLatency)s
        - Calculated Stress: \(calculateStressProbability() * 100)%
        """)
    }
}
