# Bars and the fold

Code here targets an iOS 27.1 deployment target unless a block says otherwise. "Measured" means observed in the iOS 27.1 iPhone Duo simulator.

## Vertical bars

### Placement

Apple describes vertical bars on the outer display in both orientations and on the inner display in landscape; inner portrait keeps horizontal bars. The camera determines the physical edge, and RTL changes its logical name. Read the preferred edge and the local safe area instead of reconstructing that policy from orientation. The status bar moves into the side bar, so the top safe-area inset can be 0 while the side inset is large. Read both from the view; don't assume a top inset.

Fresh iOS 27.1 simulator checks confirm symbol actions in the side bar, text/custom defaults in the horizontal bar, and opt-out restoring horizontal bars. A navigation title can still require horizontal space above the content. The edge value is a preference, independent of bar visibility; `.unspecified`/`nil` means no preferred vertical edge.

### Opting in

- The app must link the iOS 27.1 SDK.
- Bars must come from containers:
  - SwiftUI: `.toolbar` content inside `NavigationStack`, `NavigationSplitView` or `TabView`.
  - UIKit: `navigationItem` and `toolbarItems` on view controllers inside `UINavigationController`, or a `UITabBarController`.
- A `UIToolbar`, `UINavigationBar` or `UITabBar` used as a plain subview is ignored and stays horizontal (measured: inset by the side bar, never rotated).
- In a split view only the detail column's items go vertical; other columns stay horizontal, and an expanded inspector gets no side bar of its own.
- Keyboard accessory bars stay attached to the keyboard.

### Item representation and axis

- The system picks the representation: symbol items go vertical as icons, and items without a symbol stay horizontal. Set both a title and an image (a SwiftUI `Label`, or `title` and `image` on `UIBarButtonItem`); the title shows in overflow.
- An item that switches between a symbol and text (a custom Select/Done button) should stay on one axis: mark it horizontal-only. The system Edit button already does this.
- Custom views stay horizontal unless marked vertical-preferred.
  - Make sure they fit the bar's fixed width, or adapt their layout when vertical (read `toolbarVerticalEdge` inside the view).
  - A view that shows text alongside a symbol is a poor fit; a badge on a symbol often replaces an inline count.
- A horizontal-only item is hidden when no horizontal bar exists.

```swift
import SwiftUI

struct InboxView: View {
    var body: some View {
        NavigationStack {
            List(1...50, id: \.self) { Text("Message \($0)") }
                .navigationTitle("Inbox")
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Share", systemImage: "square.and.arrow.up") {}
                    }
                    // Switches between a symbol and text, so keep it on one axis.
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Select", systemImage: "checkmark.circle") {}
                    }
                    .axisBehavior(.horizontalOnly)
                    // Custom views stay horizontal unless they opt in.
                    ToolbarItem(placement: .topBarTrailing) {
                        CompassView()
                    }
                    .axisBehavior(.verticalPreferred)
                    ToolbarItem(placement: .bottomBar) {
                        Button("Compose", systemImage: "square.and.pencil") {}
                    }
                }
        }
    }
}

struct CompassView: View {
    var body: some View {
        Image(systemName: "location.north.circle")
            .accessibilityLabel("Compass")
    }
}
```

```swift
import UIKit

final class MailboxViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        let select = UIBarButtonItem(title: "Select", image: UIImage(systemName: "checkmark.circle"), primaryAction: nil, menu: nil)
        select.axisBehavior = .horizontalOnly
        let compose = UIBarButtonItem(title: "Compose", image: UIImage(systemName: "square.and.pencil"), primaryAction: nil, menu: nil)
        navigationItem.rightBarButtonItems = [select]
        toolbarItems = [.flexibleSpace(), compose]
        navigationController?.setToolbarHidden(false, animated: false)
        // In a tab bar controller, keep toolbar items visible before tabs.
        navigationItem.verticalBarCompressionBehavior = .prefersBarItems
    }
}
```

For custom back or close buttons, use the SwiftUI `.cancellationAction` placement. In UIKit, use a leading item with `leftItemsSupplementBackButton` left at `false`. Put prominent actions in `.topBarPinnedTrailing` (UIKit `pinnedTrailingGroup`); both are iOS 27.0. Pinned items can overflow when search is active and space is insufficient, as [Apple documents](https://developer.apple.com/documentation/swiftui/toolbaritemplacement/topbarpinnedtrailing).

### Turning the side bar off

SwiftUI resolves `.toolbarVerticalBehavior(_:)` from the active content:

- `NavigationStack`: the top view.
- `TabView`: the selected tab.
- `NavigationSplitView`: the trailing-most column.
- A sheet: its own content.

UIKit asks `preferredVerticalBarBehavior`. `UINavigationController` and `UITabBarController` forward it to their top or selected child; a custom container forwards it with `childForPreferredVerticalBarBehavior`. Call `setNeedsUpdateOfVerticalBarConfiguration()` when the answer changes. The system animates the change, including the safe-area inset and the status bar's axis.

```swift
import UIKit

final class CalculatorViewController: UIViewController {
    // A non-scrolling, bottom-heavy layout keeps horizontal bars.
    override var preferredVerticalBarBehavior: UIVerticalBarBehavior { .disabled }
}

final class CardContainerViewController: UIViewController {
    var content: UIViewController? {
        didSet { setNeedsUpdateOfVerticalBarConfiguration() }
    }

    override var childForPreferredVerticalBarBehavior: UIViewController? { content }
}
```

For apps with a deployment target below iOS 27.1:

```swift
import SwiftUI

extension View {
    @ViewBuilder
    func keepsHorizontalBars() -> some View {
        if #available(iOS 27.1, *) {
            toolbarVerticalBehavior(.disabled)
        } else {
            self
        }
    }
}
```

Disable only where horizontal bars serve the layout better, such as a calculator, a full-screen player with toolbar controls, or a sheet with a single button. Keep the choice stable. Don't toggle it with a view's state, and don't use it to hide bars; the visibility APIs do that.

### Compression and overflow

`toolbarVerticalCompressionBehavior(_:)` and `UINavigationItem.verticalBarCompressionBehavior` choose what compresses first when a tab bar and toolbar items share the side bar.

| Value | Meaning |
|---|---|
| SwiftUI `.automatic` | Prefers the tab bar |
| SwiftUI `.prefersToolbarItems` / UIKit `.prefersBarItems` | Tabs compress first |
| SwiftUI `.prefersTabBar` | Toolbar items compress first |

Use them as follows:

- **Navigation-focused screens** keep the default.
- **Task-focused screens**, such as compose or editing, prefer toolbar items.
- **Rechecked:** SwiftUI and UIKit preferences worked in a constrained tab/navigation fixture: preferring tabs retained all four tabs; preferring toolbar items retained bottom actions and compressed tabs. The previous observation that preferences were ignored did not reproduce. Check the preference on the active screen and compare an actually constrained pose.
- **Order within the bar** is visibility priority (swiftui-whats-new-27). By default items overflow from the bottom.
- **Overflow menus:** merge an existing app-specific overflow menu into the system one with `ToolbarOverflowMenu` or `additionalOverflowItems`, and keep the ellipsis symbol for that menu only.
- **Custom views:** check that their functionality stays reachable under compression; do not assume an arbitrary custom view has a usable system-menu representation.

Other details:

- Flexible spacers have zero length in the vertical axis; fixed spacers keep their minimum.
- With Reduce Transparency on, the system draws an opaque backing behind the side bar, slightly narrower than its inset. Keep custom content legible either way.
- Tab bar labels appear while someone scrubs the tabs in the side bar. A custom tab bar loses this, along with the compression logic.

### Custom chrome next to the system bar

UIKit can ask for the region where the system draws a bar on a given edge.

Choose the edge from `verticalBarEdge`, with a horizontal fallback when there is no preferred edge. A region for an edge without a system bar remains useful for custom chrome; it does not prove a system bar is visible. Reserve space for the controls instead of covering content.

```swift
import UIKit

final class PlayerControlsViewController: UIViewController {
    private let controls = UIStackView()
    private var regionConstraints: [NSLayoutConstraint] = []

    override func viewDidLoad() {
        super.viewDidLoad()
        controls.axis = .vertical
        controls.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(controls)
        placeControls()
        registerForTraitChanges(UITraitCollection.systemTraitsAffectingVerticalBarEdge) { (self: Self, _: UITraitCollection) in
            self.placeControls()
        }
    }

    private func placeControls() {
        let edge = traitCollection.verticalBarEdge
        controls.axis = edge == .unspecified ? .horizontal : .vertical
        let region: UIView.LayoutRegion
        switch edge {
        case .leading: region = .bar(onEdge: NSDirectionalRectEdge.leading, extent: 44)
        case .trailing: region = .bar(onEdge: NSDirectionalRectEdge.trailing, extent: 44)
        default: region = .bar(onEdge: NSDirectionalRectEdge.bottom, extent: 44)
        }
        let guide = view.layoutGuide(for: region)
        NSLayoutConstraint.deactivate(regionConstraints)
        regionConstraints = [
            controls.leadingAnchor.constraint(equalTo: guide.leadingAnchor),
            controls.trailingAnchor.constraint(equalTo: guide.trailingAnchor),
            controls.topAnchor.constraint(equalTo: guide.topAnchor),
            controls.bottomAnchor.constraint(lessThanOrEqualTo: guide.bottomAnchor),
        ]
        NSLayoutConstraint.activate(regionConstraints)
    }
}
```

SwiftUI has no equivalent bar-region API here. Read `@Environment(\.toolbarVerticalEdge)` and use local safe-area layout. See app-resizability for general safe areas and liquid-glass for glass beside the system bar.

### Sheets and the tab sidebar

Use `presentationPlacement` to express the preferred side, and let the presentation adapt to the fold and available area. Apply a screen-specific vertical-bar policy inside the presented content. These placement APIs are iOS 27.0; the vertical-bar policy is iOS 27.1.

```swift
import SwiftUI

struct FiltersButton: View {
    @State private var showsFilters = false

    var body: some View {
        Button("Filters", systemImage: "line.3.horizontal.decrease") { showsFilters = true }
            .sheet(isPresented: $showsFilters) {
                NavigationStack {
                    FiltersForm()
                        .toolbar {
                            ToolbarItem(placement: .cancellationAction) {
                                Button("Close", systemImage: "xmark") { showsFilters = false }
                            }
                        }
                }
                // One button: keep it in a horizontal bar instead of a side bar.
                .toolbarVerticalBehavior(.disabled)
                .presentationPlacement(.trailing)
            }
    }
}

struct FiltersForm: View {
    var body: some View { Form { Toggle("Unread only", isOn: .constant(false)) } }
}
```

For information-dense apps, a sidebar-adaptable tab view can prefer a sidebar when space permits.

```swift
import SwiftUI

struct LibraryTabs: View {
    var body: some View {
        TabView {
            Tab("Home", systemImage: "house") { Text("Home") }
            Tab("Browse", systemImage: "square.grid.2x2") { Text("Browse") }
        }
        .tabViewStyle(.sidebarAdaptable)
        .defaultTabBarPlacement(.sidebar)
    }
}
```

In UIKit, set `tabBarController.sidebar.preferredPlacement = .sidebar` (iOS 27.0). Watch `sidebar.isAvailable` and the delegate's `tabBarController(_:sidebarAvailabilityDidChange:)` for features that need the sidebar.

## Content margins next to the side bar

`ContentMarginGuide.container` (iOS 27.1 SDK, `anyAppleOS 27.1`) gives asymmetric content margins, so content can sit closer to the side bar while the opposite margin stays.

Do not hardcode the resulting margins.

```swift
import SwiftUI

struct ArticleBody: View {
    let text: String

    var body: some View {
        ScrollView {
            Text(text)
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentMargins(for: .container, edges: .horizontal)
        }
    }
}
```

## Reserved regions

These examples place a checkout action in a full-screen nonfold region. Keep the full button and its padding inside the chosen area. If a narrow scene or large text makes it too small, choose another usable region or adapt the screen instead of shrinking the hit target.

```swift
import SwiftUI

struct CheckoutView: View {
    var body: some View {
        GeometryReader { proxy in
            let bounds = CGRect(origin: .zero, size: proxy.size)
            // Default mirrored coordinates match SwiftUI's RTL placement.
            let fold = proxy.reservedRegions(kind: .division).first?.frame
            let area = Self.buttonArea(in: bounds, avoiding: fold)
            ZStack {
                ProductDetails()
                Button {} label: {
                    Text("Buy Now").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .padding(16)
                .frame(width: area.width, height: area.height, alignment: .bottom)
                .position(x: area.midX, y: area.midY)
            }
        }
    }

    static func buttonArea(in bounds: CGRect, avoiding division: CGRect?) -> CGRect {
        guard let division, bounds.intersects(division) else { return bounds }
        let fold = bounds.intersection(division)
        if fold.height >= fold.width {
            // Logical trailing; SwiftUI mirrors both the query and placement in RTL.
            return CGRect(x: fold.maxX, y: bounds.minY,
                          width: max(0, bounds.maxX - fold.maxX), height: bounds.height)
        }
        return CGRect(x: bounds.minX, y: fold.maxY,
                      width: bounds.width, height: max(0, bounds.maxY - fold.maxY))
    }
}

struct ProductDetails: View {
    var body: some View { Text("Product details") }
}
```

```swift
import UIKit

final class CheckoutContainerView: UIView {
    let buyButton = UIButton(configuration: .borderedProminent())

    override init(frame: CGRect) {
        super.init(frame: frame)
        buyButton.setTitle("Buy Now", for: .normal)
        addSubview(buyButton)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    override func layoutSubviews() {
        super.layoutSubviews()
        // UIKit lays out again when the fold changes, even without a size change.
        let area = regionAvoidingFold(in: bounds.inset(by: safeAreaInsets))
        let size = buyButton.intrinsicContentSize
        buyButton.frame = CGRect(x: area.midX - size.width / 2, y: area.maxY - size.height - 16, width: size.width, height: size.height)
    }

    private func regionAvoidingFold(in area: CGRect) -> CGRect {
        guard let division = reservedRegions(kind: .division).first?.frame,
              area.intersects(division) else { return area }
        let fold = area.intersection(division)
        if fold.height > fold.width {
            let leading = CGRect(x: area.minX, y: area.minY, width: max(0, fold.minX - area.minX), height: area.height)
            let trailing = CGRect(x: fold.maxX, y: area.minY, width: max(0, area.maxX - fold.maxX), height: area.height)
            return effectiveUserInterfaceLayoutDirection == .rightToLeft ? leading : trailing
        }
        return CGRect(x: area.minX, y: fold.maxY, width: area.width, height: max(0, area.maxY - fold.maxY))
    }
}
```

API:

- **SwiftUI** `GeometryProxy.reservedRegions(kind:options:layoutDirectionBehavior:)` returns `[ReservedRegion]`. Each has `id`, `kind`, `frame`, `margins` (`EdgeInsets`) and `isActive`.
- **Kinds** are `.division` and `.occlusion`. The option is `.includeInactive`.
- **UIKit** `UIView.reservedRegions(kind:options:)` returns `[UIView.ReservedRegion]`, with the same fields and `UIEdgeInsets` margins. In Objective-C: `reservedRegionsOfKind:options:` with `UIViewReservedRegionKind.divisionRegionKind`.
- **`frame`** includes the margins around the reserved rect, which pad it for touch targets.
- **Where to read:** inside `GeometryReader` or `onGeometryChange` in SwiftUI, and in `layoutSubviews` or `viewDidLayoutSubviews` in UIKit.

Fresh iOS 27.1 simulator checks:

- The default division query is empty when flat and populated when partially folded. `.includeInactive` also returns the flat division. Some current API-page prose says “regardless of active state”; the query option declaration, talk and runtime distinguish these cases.
- The division's `frame` remains 40 pt wide, including 20 pt margins on each side. Its unpadded width is zero. This does not establish a contradiction with Apple's zero-width statement, which may describe the unpadded rect. Use `isActive` or the query option rather than width.
- RTL mirrors SwiftUI's returned region geometry by default. `.fixed` keeps physical coordinates, but does not turn a SwiftUI `.position` layout into physical coordinates. Use a consistent coordinate convention throughout.
- Region reads update when folding without changing the view size. With `onGeometryChange`, include regions in the transform's observed result; a size-only result cannot signal a changed fold.

Design notes:

- **Displace only what needs it.** Move controls together when they belong together, don't move them far from their source, and leave continuous scrolling content alone.
- **Choose the side by purpose.** In book pose Apple describes alerts moving toward where they will appear when the device closes. The talk says trailing; the fresh simulator alert appeared on the leading half. Let system presentations choose their placement instead of correcting that simulator observation with manual positioning. In laptop pose, glanceable content goes in the upper region and controls in the lower.
- **Keep every control reachable in every pose.** Don't tie functionality to a pose.
- **Grids.** Apple suggests inactive regions for high-level decisions: in grid-like layouts, you could prefer an even number of columns when a division region is present, active or not (`.includeInactive`).

## Arrangements

`ArrangementView` (SwiftUI) and `UIArrangementViewController` (UIKit) lay out a primary and a secondary view from the context: size, size classes and the fold.

| Style | Behavior |
|---|---|
| `.automatic` | Resolves to `.split` |
| `.split` | Side by side when wider than tall, stacked when taller. Restrict with `.axes(_:)`. If the allowed axis can't be used, only the primary shows. |
| `.overlay` | The primary is layered over the secondary (controls over video). When the fold divides the view, the two go side by side. |

iOS 27.1 simulator observations (available poses only):

- **Flat open:** a horizontal split, at the middle of the view.
- **Partially folded:** the boundary sits on the fold's division (primary ends at x 455.5, secondary starts at 495.5).
- **Closed portrait:** stacked for an unrestricted split; horizontal-only split displays just the primary.
- **Closed landscape:** SwiftUI drew both split children in the same frame while UIKit rendered only the primary. Its secondary `state.isHidden` nevertheless stayed `false` in the direct container query; visual collapse and reported state did not agree. This reproduced in the iOS 27.1 simulator runtime; verify the constrained layout rather than relying on the environment value alone.
- **`.overlay`:**
  - It stayed layered until partially folded, then went side by side with the secondary on the leading side.
  - `.overlayArrangementEdge(_:)` (`HorizontalEdge?` or `VerticalEdge?`) selects the view's edge when the overlay transitions to a separated layout along the corresponding axis. The fresh run did not exercise it; the observation above is the default.
- **State values:** Fresh checks reproduced SwiftUI child `overlayArrangementZIndex == 0` and `splitArrangementAxis == nil` despite changed layout. Read these inside the arranged child, as the API requires; do not turn this simulator observation into a workaround based on hinge angles. UIKit provides `state(for:)`. Hardware behavior is unverified.

```swift
import SwiftUI

struct NowPlayingScreen: View {
    var body: some View {
        NavigationStack {
            ArrangementView {
                PlayerPane()
            } secondary: {
                UpNextPane()
            }
            // Only ever side by side. When the view is taller than wide, just the player shows.
            .arrangementViewStyle(.split.axes(.horizontal))
            .navigationTitle("Now Playing")
        }
    }
}

struct PlayerPane: View {
    var body: some View {
        Text("Player")
            .splitArrangementLayoutRatio(0.6)
    }
}

struct UpNextPane: View {
    @Environment(\.splitArrangementAxis) private var axis

    var body: some View {
        Text(axis == .horizontal ? "Up Next, beside the player" : "Up Next")
    }
}

struct VideoScreen: View {
    var body: some View {
        ArrangementView {
            PlaybackControls()
        } secondary: {
            Color.black
        }
        .arrangementViewStyle(.overlay)
    }
}

struct PlaybackControls: View {
    @Environment(\.overlayArrangementZIndex) private var zIndex

    var body: some View {
        // Layered over the video: zIndex > 0. Beside it after a fold: 0.
        Text("Controls")
            .padding()
            .background(zIndex > 0 ? AnyShapeStyle(.ultraThinMaterial) : AnyShapeStyle(.background))
    }
}
```

```swift
import UIKit

final class UpNextViewController: UIViewController {
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        guard let arrangement = arrangementViewController,
              let placement = arrangement.placement(for: self),
              let state = arrangement.state(for: placement) else { return }
        // Collapsed while layered over the player, expanded once a fold puts it beside the player.
        setExpanded(state.zIndex == 0 && !state.isHidden)
    }

    private func setExpanded(_ expanded: Bool) {}
}

@MainActor
func makeNowPlaying(player: UIViewController) -> UIViewController {
    let arrangement = UIArrangementViewController()
    arrangement.setViewController(player, for: .primary)
    arrangement.setViewController(UpNextViewController(), for: .secondary)
    arrangement.updateArrangement(.overlay)
    return UINavigationController(rootViewController: arrangement)
}
```

Choosing:

- **Split** for a main-detail pair where neither may be covered, such as a player with a transcript.
- **Overlay** for a foreground over a background that may be covered, such as controls over video or readable content.
- **Existing patterns:** an existing `HStack`/`VStack` split maps to a split arrangement, and a `ZStack` maps to an overlay.

Placement and support:

- Arrangements provide no navigation. Don't put `NavigationSplitView` inside one, and don't put one inside `List` or `ScrollView`.
- Split sizing: `splitArrangementLayoutRatio`, `splitArrangementLayoutSize` and `splitArrangementFixedLayoutSize`; in UIKit, `UISplitArrangement.ViewProperties`.
- Arrangements run on every iOS 27.1 device and pick a single view or a split by space.

## Hinge

```swift
import SwiftUI

struct WhammyGuitarView: View {
    // Start with no bend; do not require an initial callback on a device without a hinge.
    @State private var pitchBend = 0.0

    var body: some View {
        GuitarStrings(pitchBend: pitchBend)
            .onHingeChange { _, context in
                if let hinge = context.hinge, hinge.status == .partiallyOpen {
                    pitchBend = (180 - hinge.angle.degrees) / 180
                } else {
                    pitchBend = 0
                }
            }
    }
}

struct GuitarStrings: View {
    let pitchBend: Double
    var body: some View { Text("Bend \(pitchBend, format: .number.precision(.fractionLength(2)))") }
}
```

```swift
import UIKit

final class InstrumentViewController: UIViewController {
    private var pitchBend: CGFloat = 0

    override func viewDidLoad() {
        super.viewDidLoad()
        let interaction = UIHingeInteraction { [weak self] _, update in
            guard let self else { return }
            // nil when the view leaves a hierarchy that provides hinge updates. The angle is in radians.
            if let hinge = update.hinge, hinge.status == .partiallyOpen {
                pitchBend = (.pi - hinge.angle) / .pi
            } else {
                pitchBend = 0
            }
        }
        view.addInteraction(interaction)
    }
}
```

API:

- **SwiftUI:**
  - `onHingeChange(isEnabled:_:)` passes the old and new `DeviceHingeContext`.
  - `context.hinge` is a `DeviceHinge?`, with `status` (`.closed`, `.partiallyOpen`, `.fullyOpen`) and `angle` (`Angle`).
- **UIKit:**
  - `UIHingeInteraction(updateHandler:)` passes the interaction and a `UIHingeInteraction.Update`.
  - `update.hinge` is a `UIHinge?`, with `status` (adds `.unknown`) and `angle` (`CGFloat`, radians).
  - `isEnabled` pauses updates without queueing them.
- **Not an API:** the `handleHingeUnavailable()` in Apple's header example is a placeholder for your own code.
- **Rate and precision** of angle updates are system policy and change with system state.

Measured:

- **Initial call:** the Duo handlers delivered current state. On the nonfoldable iPhone 17 Pro simulator running iOS 27.2, the initialized callback count stayed zero during the bounded observation. Initialize nonfoldable behavior without depending on a callback.
- **`fullyOpen`** appeared only at 180°.
- **Status exhibited hysteresis in the simulator, rather than a unique angle-to-status mapping:**
  - Opening in small steps stayed `closed` up to 118° on the outer display.
  - Jumping straight to 90° gave `partiallyOpen` on the inner display.
  - Closing from open stayed `partiallyOpen` at the measured 47.5°.
- **Display switch:** the move between displays coincided with the change between `closed` and `partiallyOpen`.
- This is not by itself a contradiction: the API promises status and angle, not a specific threshold or a path-independent mapping. Do not implement layout or duplicate the system's display-switch policy from these measurements.
- **Use:** interactions and visual effects (a pitch bend, a wallpaper zoom). Use reserved regions and arrangements for layout, and `status` rather than angle thresholds for decisions.
