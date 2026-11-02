---
name: iphone-duo
description: "iPhone Duo (Apple's foldable iPhone, iOS 27.1 SDK): side bars, fold avoidance, arrangements, hinge, dual-display camera UI and camera direction. General resizing belongs to app-resizability."
---

# iPhone Duo

Use this skill for the behavior being changed. A broad “get my app ready for Duo” request starts with **app-resizability**; do not turn a working symbol toolbar over a `List` into custom chrome merely to support Duo.

## Build, deployment and runtime

- **Baseline:** Xcode 27.1 or later, iOS 27.1 SDK or later, Swift 6.4. Select it explicitly when multiple Xcodes are installed. Building with this SDK enables the full-display and vertical-bar behavior; raising the deployment target alone does not.
- **Deployment:** guard the Duo APIs with `if #available(iOS 27.1, *)` or annotate their declarations. These related APIs are iOS 27.0: `presentationPlacement`, `defaultTabBarPlacement`, sidebar `preferredPlacement`, `topBarPinnedTrailing`. Availability cannot supply a symbol missing from the build SDK.
- **Mac Catalyst:** isolate affected 27.1 APIs with `#if !targetEnvironment(macCatalyst)`; the Xcode 27.1 and 27.2 release notes still list the Catalyst compile errors as a known issue (185924957). [Apple release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes).
- **Runtime:** iPhone Duo ships with iOS 27.1 and runs only on Duo-only simulator runtimes; the general iOS runtimes run the other iPhones. A nonfoldable simulator is a separate comparison, not proof of Duo runtime behavior.

Closed Duo has compact width; open Duo has regular width and height while its idiom remains `.phone`. General resizing belongs to app-resizability. The linked-SDK and `UIRequiresFullScreen`/orientation matrix is in [displays-and-camera.md](references/displays-and-camera.md#apps-by-linked-sdk).

## Vertical bars

Read [bars-and-fold.md](references/bars-and-fold.md#vertical-bars) when implementing or reviewing bars.

- **Containers supply the bar:** SwiftUI toolbar content in a navigation/tab container; UIKit `navigationItem` and `toolbarItems` in `UINavigationController`/`UITabBarController`. A `UIToolbar`, `UINavigationBar` or `UITabBar` added as a subview stays horizontal. A navigation controller's bottom toolbar must also be shown with `setToolbarHidden(false, animated:)`.
- **Representation:** symbol buttons normally move to the side. Text-only and custom-view items stay horizontal. Opt a fitting custom item in with `.axisBehavior(.verticalPreferred)` on `ToolbarContent`, or `UIBarButtonItem.axisBehavior`; `.horizontalOnly` keeps one horizontal. Supply titles for accessible names and overflow. Custom views need their own reachable alternative if they disappear under compression.
- **Screen opt-out:** `.toolbarVerticalBehavior(.disabled)` or override `preferredVerticalBarBehavior`. UIKit custom containers forward through `childForPreferredVerticalBarBehavior`; invalidate changes with `setNeedsUpdateOfVerticalBarConfiguration()`. Use visibility APIs to hide bars.
- **Shared bar compression:** `.toolbarVerticalCompressionBehavior(.prefersToolbarItems)` / `navigationItem.verticalBarCompressionBehavior = .prefersBarItems` prefers actions over tabs. This is a preference under available space, not a guarantee that every action remains visible. The talk's `toolbarCompressionBehavior` spelling is not the SDK API.
- **Edge and clearance:** read `toolbarVerticalEdge` / `traitCollection.verticalBarEdge`, not orientation. They report the preferred edge even when a bar is hidden; `nil` / `.unspecified` means no preferred vertical edge. Read local safe-area insets separately. UIKit custom chrome can use `view.layoutGuide(for: .bar(onEdge:extent:))`. General safe-area handling belongs to app-resizability; glass shape and Reduce Transparency to liquid-glass.
- **Overflow:** swiftui-whats-new-27 covers `visibilityPriority` and `ToolbarOverflowMenu`. Pinned trailing items can still overflow during active search if space runs out. [Apple placement documentation](https://developer.apple.com/documentation/swiftui/toolbaritemplacement/topbarpinnedtrailing).

## Fold layout and hinge input

Read [bars-and-fold.md](references/bars-and-fold.md#reserved-regions) for SwiftUI/UIKit examples.

1. Prefer system presentation and navigation components, which adapt around the fold. Continuous scrolling content generally need not avoid it.
2. For two panes, use `ArrangementView` / `UIArrangementViewController`. Split is for content that should not overlap; overlay is for a foreground over a background. Restrict split axes when only side-by-side makes sense. Keep navigation outside the arrangement and scrolling inside its panes.
3. For individual controls, query `.division` reserved regions. Query from the view whose coordinate space you use. `frame` already includes touch margins; do not add them twice. Use active state/query options, not frame width, to decide whether avoidance is needed.
4. Use `onHingeChange` / `UIHingeInteraction` for interactions and effects, not layout. SwiftUI provides `Angle`, UIKit radians. Initialize a useful no-hinge state; a nonfoldable device may never call the handler. Prefer status to invented angle thresholds.

Fold changes can occur without a size change. Read regions in layout; an `onGeometryChange` transform must include the region data you care about, not only `size`. SwiftUI mirrors region coordinates by default for RTL; use `.fixed` only when your placement also uses physical coordinates. UIKit frames are physical. Test the control's complete bounds, not only its center.

## Scenes and cameras

Read [displays-and-camera.md](references/displays-and-camera.md#scenes-and-multitasking) for code and preconditions.

- A display transition resizes the existing scene. Keep state outside branches that replace view identity.
- New-window UI should use `UIWindowScene.ActivationAction` and handle activation errors. Pass `alternate: nil` to select its configuration-provider initializer unambiguously. A void trailing closure with `title:` alone binds the inherited `UIAction` handler initializer and can crash during initialization. The activation action itself is iOS 15.0, not a new 27.1 API.
- Both displays at once require the camera capture scene accessory: `CameraCaptureAccessory` in `.sceneAccessory { }`, or `UISceneAccessory.cameraCapture(sceneConfiguration:)`. Apple's conditions are an active capture session and a foreground app full screen on the inner display. Observe availability; simulator availability without a camera does not establish presentation eligibility on hardware.
- Existing front-camera discovery uses a virtual camera that follows the app between displays. Choose physical inner/outer camera types only when their full capabilities are needed. `AVCaptureDeviceDirectionCoordinator` (AVKit) reports direction relative to a preview view; position alone cannot choose the camera or mirroring.
- The coordinator belongs on the main actor. Pass its Sendable descriptors/maps to the serialized capture owner, resolve devices there, and apply mirroring there on direction changes and new connections. **swift-concurrency** owns the capture actor design.

`ContentMarginGuide.container` (iOS 27.1) gives asymmetric content margins next to the side bar; see [content margins](references/bars-and-fold.md#content-margins-next-to-the-side-bar).

## Verification

Run `XCODE=/path/to/Xcode.app tests/run.sh` with the Xcode you build with, for the examples and availability gates. Compiler success does not validate bar placement or camera behavior.

Use **mobilecli** for pose tests and the [simulator recipe and limits](references/displays-and-camera.md#testing-on-the-simulator). Capture both displays, test closed/open/partially folded, RTL and relevant accessibility settings. Keep SDK, deployment target, runtime build, Info.plist choices and pose sequence with observations. Simulator-only anomalies in the references are observations, not platform contracts. When Apple docs, SDK declarations and runtime observations conflict, resolve each claim on its own evidence.
