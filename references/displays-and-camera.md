# Displays, scenes, camera, testing

"Measured" means observed in the iOS 27.1 iPhone Duo simulator (Xcode 27.1 beta).

## Apps by linked SDK

| Linked SDK | Closed (outer display) | Open (inner display) | Size classes (closed / open) |
|---|---|---|---|
| iOS 26.x | 375×667 window at the leading edge, left of the status bar, black beside it | The same 375×667 window centered with black on both sides, no reaction to poses | compact/regular, compact/regular |
| iOS 27.0 | 386×678, left of the status bar, black strip under it | 871×669 from the leading edge, black strip (80 pt) under the trailing status bar, horizontal bars | compact/regular, regular/regular |
| iOS 27.1 | 466×678, full screen, side bar | 951×669, full screen, side bar | compact/regular, regular/regular |

All measured. Notes:

- Apple describes the iOS 26 window as an older iPhone's size and aspect ratio. Its zoom control doesn't make the app respond to poses.
- Once an app links an iOS 27 SDK, resizing can't be turned off.
- For apps that are not ready yet, Apple's advice is to make them resizable first and tune for poses later.

Supported orientations and `UIRequiresFullScreen`, measured with iOS 27.1 SDK builds:

| Info.plist | Closed | Open |
|---|---|---|
| All orientations | Portrait 466×678 | Landscape 951×669, full screen |
| Portrait only | Portrait 466×678 | Landscape 951×669, full screen: the orientation list is ignored |
| Portrait only + `UIRequiresFullScreen` | Portrait 466×678 | Portrait 669×951 window scaled to about 0.7, black on both sides |
| All orientations + `UIRequiresFullScreen` | Portrait 466×678 | Landscape 951×669, full screen |

Notes:

- **Apple** says the scaling also applies in split view. That wasn't reproducible here.
- **Programmatic orientation:** `UIWindowScene.requestGeometryUpdate` with a portrait mask fails on the inner display with `UISceneErrorDomain` code 101, "The current windowing mode does not allow for programmatic changes to interface orientation". On the outer display it rotates the app, if the app supports that orientation.
- **Interface orientation** is still reported through the trait collection and the scene's geometry. Use size classes and sizes for layout (app-resizability).

## Scenes and multitasking

- **Opening and closing resizes the scene the app already has.** Nothing is torn down or recreated.
  - In SwiftUI, a view that picks a different container in each branch of an `if` on size class loses the losing branch's state when the device opens or closes. Hoist the state, or keep one container.
- **Split view.** The inner display splits 50/50 between two apps, or two scenes of one app. Each side is a resizable scene, and the left one gets a leading side bar.
  - When the device closes, the app in use moves to the outer display and the other goes to the background.
  - If the device is reopened soon, both return. After a while, the app on the outer display takes the whole inner display.
- **Multiple windows** work as on iPad, and scenes of one app share state as they do there.
  - Apple: new windows can only be created on the inner display. Enable `UIApplicationSupportsMultipleScenes` in the scene manifest and provide scene configuration for new sessions. Handle activation errors, and prefer `UIWindowScene.ActivationAction` (Objective-C `UIWindowSceneActivationAction`), which hides itself when new windows aren't available.
  - Rechecked: a direct activation request on the outer display succeeded and replaced the visible scene. The activation-action button stayed visible there, but tapping it did not invoke its configuration provider. On the inner display the correct action opened a side-by-side split. Keep these distinct outcomes separate from Apple's documented restrictions.

`UIWindowScene.ActivationAction` is available since iOS 15.0. The code below targets iOS 27.1, including its separate scene-request call.

```swift
import UIKit

@MainActor
func makeNewWindowButton(for document: NSUserActivity) -> UIButton {
    // Pass `alternate:` (or another argument only this initializer has). Without it the trailing closure
    // can bind to UIAction's unsupported handler initializer and crash during initialization.
    let action = UIWindowScene.ActivationAction(title: "Open in New Window", alternate: nil) { _ in
        UIWindowScene.ActivationConfiguration(userActivity: document)
    }
    return UIButton(configuration: .bordered(), primaryAction: action)
}

@MainActor
func openWindow(for document: NSUserActivity) {
    let request = UISceneSessionActivationRequest(role: .windowApplication, userActivity: document, options: nil)
    UIApplication.shared.activateSceneSession(for: request) { error in
        // Handle rejection wherever window creation is unavailable.
        print("Couldn't open a window: \(error.localizedDescription)")
    }
}
```

## Showing UI on the other display

Camera apps can present interactive content on both displays through the camera capture scene accessory (iOS 27.1). This is not a general secondary-display API for non-camera apps.

Apple's conditions for the accessory:

- The app is in the foreground, full screen on the inner display.
- The app has an active camera capture session.
- The device is not in split view.
- The system decides whether and where to present it.

The accessory is a full, interactive scene with no widget-style limits on content or animation. Register it on the view that shows the camera UI, so it appears only while that view does. The system presents the registration of the topmost, most recently presented view controller.

```swift
import SwiftUI

struct RehearsalCameraView: View {
    @State private var showsTeleprompter = true
    @State private var teleprompterAvailable = false

    var body: some View {
        NavigationStack {
            CameraPreviewArea()
                .toolbar {
                    Button("Teleprompter", systemImage: "text.alignleft") { showsTeleprompter.toggle() }
                        .disabled(!teleprompterAvailable)
                }
                .sceneAccessory {
                    CameraCaptureAccessory(isEnabled: $showsTeleprompter) {
                        TeleprompterText()
                    }
                    .onAvailabilityChange { teleprompterAvailable = $0 }
                }
        }
    }
}

struct CameraPreviewArea: View {
    var body: some View { Color.black }
}

struct TeleprompterText: View {
    var body: some View { Text("Your lines").font(.largeTitle) }
}
```

```swift
import UIKit

final class CaptureViewController: UIViewController {
    private var teleprompter: UISceneAccessoryRegistration?

    override func viewDidLoad() {
        super.viewDidLoad()
        let configuration = UISceneConfiguration()
        configuration.delegateClass = TeleprompterSceneDelegate.self
        teleprompter = registerSceneAccessory(.cameraCapture(sceneConfiguration: configuration))
    }

    override func updateProperties() {
        super.updateProperties()
        // isAvailable is observed here and in layoutSubviews.
        navigationItem.rightBarButtonItem?.isEnabled = teleprompter?.isAvailable ?? false
    }
}

final class TeleprompterSceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        // The system gives this session the .windowCameraCaptureAccessory role.
        guard let windowScene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = UIViewController()
        window.makeKeyAndVisible()
        self.window = window
    }
}
```

UIKit details:

- `registration.isEnabled` turns the content off and on without giving up the registration.
- `unregisterSceneAccessory(_:)` removes it.
- `cameraCapture(sceneConfiguration:userInfo:)` passes context, which the delegate reads from `connectionOptions.sceneAccessoryUserInfo`.

Rechecked on iOS 27.1 (24A94401): with zero discovered cameras and no capture session, both SwiftUI and UIKit accessories reported available on the inner display and actually presented content on the outer display. The earlier “nothing presented” observation did not reproduce. This simulator behavior does not relax Apple's active-camera condition for hardware. Observe availability and verify real capture/presentation on a device.

## Cameras

iPhone Duo has two front cameras, both square-sensor ultra wides:

| Camera | Device type (iOS 27.1) | Video |
|---|---|---|
| Outer front camera | `.builtInOuterUltraWideCamera` | Up to 4K, 120 fps |
| Inner front camera (under the inner display) | `.builtInInnerUltraWideCamera` | 1080p, up to 60 fps |
| Virtual front camera | Returned for `.builtInWideAngleCamera` / `.builtInUltraWideCamera` at `.front` | Only what both share: 1080p, 60 fps |

Notes:

- **Physical types** are found only through `AVCaptureDevice.DiscoverySession`.
- **Depth** is available only from the physical cameras.
- **The virtual front camera** is a virtual device (`isVirtualDevice` is `true`). It streams from the camera above the display the app is on and switches when the device opens or closes. `activePrimaryConstituent` tells which camera is streaming (nil until the session runs).
- **Existing front-camera code** keeps working unchanged through it.

```swift
import AVFoundation

func frontCamera() -> AVCaptureDevice? {
    // On iPhone Duo these types return the virtual front camera.
    AVCaptureDevice.DiscoverySession(
        deviceTypes: [.builtInWideAngleCamera, .builtInUltraWideCamera],
        mediaType: .video,
        position: .front
    ).devices.first
}
```

### Direction instead of position

A camera's `position` describes where it sits, not where it points. On iPhone Duo a "front" camera can face away from the person, for example the outer camera while the app is on the inner display. A rear camera can face the person when the app runs on the outer display with the device open.

`AVCaptureDeviceDirectionCoordinator` (AVKit, iOS 27.1) groups cameras by whether they face the same way as a given view:

- **Create it on the main actor,** with the view that shows the preview and the built-in device types you capture from. Include rear cameras.
- **On Duo, include the physical front camera types** instead of relying on its virtual front camera, which the coordinator omits. For a shared implementation, also include the ordinary front and rear camera types your app captures from; a Duo-only type list has no ordinary front-camera candidate.
- **Hold a strong reference** while the view is on screen. With a preview on each display, create one coordinator per view.
- **The handler runs on the main actor** soon after creation and on every change. `deviceDirections` is empty until that first call.
- **Hand descriptors to the session's actor.** `AVCaptureDeviceDescriptor` and `AVCaptureDeviceDirectionMap` are Sendable. Don't call AVFoundation in the handler; resolve the descriptor (`uniqueID`) on the actor that owns the session.
- **On a single-display iPhone,** front cameras are forward-facing and back cameras backward-facing, and the handler fires once. The same code runs everywhere.

```swift
import AVFoundation
import AVKit
import UIKit

@MainActor
final class CameraDirectionObserver {
    private var coordinator: AVCaptureDeviceDirectionCoordinator?
    private let receive: @MainActor (AVCaptureDeviceDirectionMap) -> Void

    // Enqueue these Sendable maps to the app's existing serialized capture owner.
    init(receive: @escaping @MainActor (AVCaptureDeviceDirectionMap) -> Void) {
        self.receive = receive
    }

    func start(previewView: UIView, deviceTypes: [AVCaptureDevice.DeviceType]) {
        coordinator = AVCaptureDeviceDirectionCoordinator(
            view: previewView,
            deviceTypes: deviceTypes
        ) { [weak self] directions in
            self?.receive(directions)
        }
    }
}
```

On the capture owner, compare the applied device with `forwardFacingDeviceDescriptors`, select a replacement if necessary, and resolve it with `AVCaptureDevice(uniqueID:)`. Handle a missing device and configuration failure. Record the applied camera only after a successful switch. Preserve the latest requested direction when updates overlap; launching independent `Task`s does not establish FIFO ordering. Reconfigure one video input rather than introducing a multi-camera session for this purpose. Keep blocking capture work off the main actor.

The connection mirrors any `.front` camera automatically. For a selfie-style preview, explicitly mirror forward-facing cameras and unmirror backward-facing ones. Update both directions, including when a previous override now agrees with the physical position. Turn off automatic adjustment before setting `isVideoMirrored`, or the assignment raises an exception. Reapply after every input change, because the new connection doesn't keep the override. Mask the preview while switching cameras.

```swift
import AVFoundation
import AVKit

// Call on the owner of the capture connection, not in the coordinator callback.
nonisolated func applyMirroring(on connection: AVCaptureConnection, for device: AVCaptureDevice, directions: AVCaptureDeviceDirectionMap) {
    guard connection.isVideoMirroringSupported else { return }
    let facesViewer = directions.forwardFacingDeviceDescriptors.contains { $0.uniqueID == device.uniqueID }
    let facesAway = directions.backwardFacingDeviceDescriptors.contains { $0.uniqueID == device.uniqueID }
    guard facesViewer || facesAway else { return }
    connection.automaticallyAdjustsVideoMirroring = false
    connection.isVideoMirrored = facesViewer
}
```

### Rotation, compensation, preview

- **Rotation coordinator.** Use `AVCaptureDevice.RotationCoordinator` for preview and capture angles. On iPhone Duo its angles also change when the app moves between displays. Create a new one whenever you switch devices.
- **Sensor-orientation compensation** is on for every iPhone Duo front camera. Once the rotation coordinator handles rotation, turn it off for performance. The photo-output property is iOS 26.
- **Rear-camera preview on the inner display.** The full field of view leaves room around the preview. Offset it and group controls in the space, or fill the display. `AVCaptureVideoPreviewLayer.videoGravity` decides.
- **Front cameras on the inner display.** The square sensors can fill it: pick a landscape `dynamicAspectRatio` (iOS 26) on the device.
- **Inner FaceTime camera.** It is a reserved occlusion region while active (see bars-and-fold.md). Keep important content and self-view thumbnails clear of it, and direct the person's gaze toward it in video calls.

```swift
import AVFoundation

func turnOffSensorCompensation(on photoOutput: AVCapturePhotoOutput) {
    // Do this only after AVCaptureDevice.RotationCoordinator drives your rotation.
    if photoOutput.isCameraSensorOrientationCompensationSupported {
        photoOutput.isCameraSensorOrientationCompensationEnabled = false
    }
}
```

Rechecked: camera discovery returned no devices in the iOS 27.1 simulator. Physical camera discovery and direction APIs compile with the 27.1 SDK; that does not exercise capture, switching, mirroring or frame delivery. Those behaviors require hardware verification against Apple's [camera-direction guide](https://developer.apple.com/documentation/avkit/choosing-a-camera-by-the-direction-it-faces).

## Testing on the simulator

- **Runtime.** iPhone Duo needs the iOS 27.1 simulator runtime from Xcode 27.1, and that runtime runs no other iPhone. The iOS 27.2 runtime in Xcode 27.2 beta 2 runs other iPhones but not iPhone Duo. Use one of those as a non-foldable baseline, building the app with the iOS 27.2 SDK minus the two missing APIs.
- **Boot state.** The simulator boots closed. Its displays are `--display=1` (outer, 466×678 pt) and `--display=3` (inner, 951×669 pt).

```bash
UDID=$(xcrun simctl create "Duo test" com.apple.CoreSimulator.SimDeviceType.iPhone-Duo com.apple.CoreSimulator.SimRuntime.iOS-27-1)
xcrun simctl boot "$UDID"
mobilecli agent install --device "$UDID"         # once per simulator
mobilecli device fold open --device "$UDID"      # folded | half-open | open | 0-180
xcrun simctl io "$UDID" screenshot --display=3 inner.png
xcrun simctl io "$UDID" screenshot --display=1 outer.png
```

Limits found:

- **Hinge angles.** `mobilecli device fold` angles are quantized: 15 arrives as 19.2° and 120 as 118.3°. 0, 90 and 180 are exact.
- **Rotation.** Device rotation commands (`mobilecli device orientation set`, Xcode's device interaction `orientation`) don't reach apps on the iPhone Duo simulator.
  - For the outer display in landscape, make the app restrict `supportedInterfaceOrientations` and call `requestGeometryUpdate` from a debug launch argument.
  - The inner display stays landscape, so the open-portrait pose (with its horizontal bars) can't be tested.
- **Not available:** split view by dragging the home indicator; cameras; StandBy; most app extensions; accessibility tools reading the screen in Device Hub.
- **Screenshot timing.** Screenshots can be black for a few minutes after boot.
- **Previews.** Xcode 27.1's canvas overrides have a Display group for previewing on the alternative display.

Before the simulator, or alongside it:

- **iPad window resizing** shows how the app handles arbitrary sizes.
- **iPhone Mirroring on the Mac** resizes an iPhone app while it keeps the phone idiom and traits, close to what iPhone Duo gives.
- **Locked-portrait apps** should test landscape for leading and trailing insets they never handled.
