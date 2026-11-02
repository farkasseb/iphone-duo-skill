#!/usr/bin/env python3
"""Compile probes for the iphone-duo skill.

Run through tests/run.sh, which selects the Xcode. Every check prints PASS or
FAIL; the exit status is non-zero if any check fails.

Sections:
  sdk       the selected iOS SDK is 27.1 or later and declares the iPhone Duo APIs
  snippets  every ```swift block in SKILL.md and references/ compiles with no
            diagnostics (swiftc -emit-sil, iOS SDK, Swift 6 mode); a block without
            a probe fails
  gates     availability: each API fails one release below the version the skill states
  names     names from Apple's talks that differ from the SDK keep failing, and the
            ActivationAction initializer pitfall still binds the way the skill says
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
DEV = os.environ.get("DEVELOPER_DIR", "")
RESULTS = []
WORK = Path(tempfile.mkdtemp(prefix="iphone-duo-probes-"))
SDK = ""


def report(section, name, ok, detail=""):
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  [{section}] {name}")
    if not ok and detail:
        print(textwrap.indent(detail.strip()[:1500], "      "))


def run(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def compile_ios(src, target="27.1", mode="6", sil=True):
    """Compile for iOS; returns (returncode, [(severity, message)], raw stderr)."""
    path = WORK / f"probe{len(RESULTS)}_{abs(hash(src)) % 10**8}.swift"
    path.write_text(src)
    cmd = ["xcrun", "swiftc", "-parse-as-library", "-emit-sil" if sil else "-typecheck"]
    if sil:
        cmd += ["-o", os.devnull]
    cmd += ["-swift-version", mode, "-sdk", SDK, "-target", f"arm64-apple-ios{target}", str(path)]
    r = run(cmd)
    diags = re.findall(r"^\S+\.swift:\d+:\d+: (error|warning): (.*)$", r.stderr, re.M)
    return r.returncode, diags, r.stderr


def expect_clean(section, name, src, **kw):
    rc, diags, err = compile_ios(src, **kw)
    report(section, name, rc == 0 and not diags, err)


def expect_diag(section, name, src, needles, severity="error", **kw):
    rc, diags, err = compile_ios(src, sil=False, **kw)
    msgs = [m for s, m in diags if s == severity]
    ok = all(any(n in m for m in msgs) for n in needles)
    if severity == "error":
        ok = ok and rc != 0
    report(section, name, ok, err)


# ---------------------------------------------------------------- toolchain and SDK

def interface(framework):
    return Path(SDK) / f"System/Library/Frameworks/{framework}.framework/Modules/{framework}.swiftmodule/arm64e-apple-ios.swiftinterface"


def header(framework, name):
    return Path(SDK) / f"System/Library/Frameworks/{framework}.framework/Headers/{name}"


def declares(path, needle):
    try:
        return needle in path.read_text(errors="ignore")
    except FileNotFoundError:
        return False


def check_toolchain():
    out = run(["xcrun", "swiftc", "--version"])
    text = out.stdout + out.stderr
    print(f"DEVELOPER_DIR={DEV or '(xcode-select default)'}")
    print(text.strip().splitlines()[0] if text.strip() else "no swiftc found")
    version = run(["xcrun", "--sdk", "iphoneos", "--show-sdk-version"]).stdout.strip()
    print(f"iOS SDK {version}: {SDK}")
    parts = [int(p) for p in version.split(".")[:2]] if version else [0, 0]
    if parts < [27, 1]:
        print("These probes need the iOS 27.1 SDK or later (Xcode 27.1). Set XCODE or DEVELOPER_DIR.")
        sys.exit(2)


def check_sdk():
    s = "sdk"
    core = [
        ("UIKit UIHingeInteraction", header("UIKit", "UIHingeInteraction.h"), "@interface UIHingeInteraction"),
        ("UIKit UIViewReservedRegion", header("UIKit", "UIViewReservedRegion.h"), "@interface UIViewReservedRegion"),
        ("UIKit UIArrangementViewController", header("UIKit", "UIArrangementViewController.h"), "@interface UIArrangementViewController"),
        ("UIKit verticalBarEdge", header("UIKit", "UIVerticalBarEdge.h"), "verticalBarEdge"),
        ("UIKit preferredVerticalBarBehavior", header("UIKit", "UIViewController.h"), "preferredVerticalBarBehavior"),
        ("UIKit layoutRegionForBarOnEdge", header("UIKit", "UIViewLayoutRegion.h"), "layoutRegionForBarOnEdge"),
        ("UIKit cameraCaptureSceneAccessory", header("UIKit", "UISceneAccessory.h"), "cameraCaptureSceneAccessoryWithConfiguration"),
        ("SwiftUI onHingeChange", interface("SwiftUICore"), "func onHingeChange("),
        ("SwiftUI ArrangementView", interface("SwiftUICore"), "struct ArrangementView<"),
        ("SwiftUI ReservedRegion", interface("SwiftUICore"), "public struct ReservedRegion"),
        ("SwiftUI toolbarVerticalBehavior", interface("SwiftUI"), "func toolbarVerticalBehavior("),
        ("SwiftUI CameraCaptureAccessory", interface("SwiftUI"), "struct CameraCaptureAccessory<"),
        ("AVFoundation builtInInnerUltraWideCamera", header("AVFoundation", "AVCaptureDevice.h"), "AVCaptureDeviceTypeBuiltInInnerUltraWideCamera"),
        ("AVKit AVCaptureDeviceDirectionCoordinator", header("AVKit", "AVCaptureDeviceDirectionCoordinator.h"), "@interface AVCaptureDeviceDirectionCoordinator"),
        ("SwiftUI ContentMarginGuide", interface("SwiftUICore"), "struct ContentMarginGuide"),
    ]
    for name, path, needle in core:
        report(s, f"SDK declares {name}", declares(path, needle), f"{needle!r} not found in {path}")


# ---------------------------------------------------------------- snippets

def swift_blocks():
    blocks = []
    for f in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]:
        text = f.read_text()
        for m in re.finditer(r"```swift\n(.*?)```", text, re.S):
            blocks.append((f.relative_to(SKILL).as_posix(), textwrap.dedent(m.group(1))))
    return blocks


B = "references/bars-and-fold.md"
D = "references/displays-and-camera.md"
# (file, marker unique to the block, prelude, deployment target)
SNIPPETS = [
    (B, "struct InboxView", "", "27.1"),
    (B, "final class MailboxViewController", "", "27.1"),
    (B, "final class CalculatorViewController", "", "27.1"),
    (B, "func keepsHorizontalBars", "", "18.0"),
    (B, "final class PlayerControlsViewController", "", "27.1"),
    (B, "struct FiltersButton", "", "27.1"),
    (B, "struct LibraryTabs", "", "27.1"),
    (B, "struct ArticleBody", "", "27.1"),
    (B, "struct CheckoutView", "", "27.1"),
    (B, "final class CheckoutContainerView", "", "27.1"),
    (B, "struct NowPlayingScreen", "", "27.1"),
    (B, "final class UpNextViewController", "", "27.1"),
    (B, "struct WhammyGuitarView", "", "27.1"),
    (B, "final class InstrumentViewController", "", "27.1"),
    (D, "func makeNewWindowButton", "", "27.1"),
    (D, "struct RehearsalCameraView", "", "27.1"),
    (D, "final class CaptureViewController", "", "27.1"),
    (D, "func frontCamera", "", "27.1"),
    (D, "final class CameraDirectionObserver", "", "27.1"),
    (D, "func applyMirroring", "", "27.1"),
    (D, "func turnOffSensorCompensation", "", "27.1"),
]


def check_snippets():
    blocks = swift_blocks()
    used = set()
    for f, marker, prelude, target in SNIPPETS:
        matches = [i for i, (bf, code) in enumerate(blocks) if bf == f and marker in code]
        name = f"{f} «{marker}»" + (f" at iOS {target}" if target != "27.1" else "")
        if len(matches) != 1:
            report("snippets", name, False, f"expected exactly one block containing the marker, found {len(matches)}")
            continue
        used.add(matches[0])
        expect_clean("snippets", name, prelude + blocks[matches[0]][1], target=target)
    for i, (f, code) in enumerate(blocks):
        if i not in used:
            report("snippets", f"{f} block {code.splitlines()[0][:50]!r} has a probe", False,
                   "add a SNIPPETS entry for this block")


# ---------------------------------------------------------------- gates

GATED = [
    # (name, source, version the skill states)
    ("UIWindowScene.ActivationAction", 'import UIKit\n@MainActor func f() { _ = UIWindowScene.ActivationAction(title: "New", alternate: nil) { _ in nil } }', "15.0"),
    ("onHingeChange", "import SwiftUI\nfunc f(v: some View) -> some View { v.onHingeChange { _, _ in } }", "27.1"),
    ("DeviceHinge", "import SwiftUI\nfunc f(h: DeviceHinge) -> Double { h.angle.degrees }", "27.1"),
    ("UIHingeInteraction", "import UIKit\n@MainActor func f() { _ = UIHingeInteraction { _, _ in } }", "27.1"),
    ("GeometryProxy.reservedRegions", "import SwiftUI\nfunc f(p: GeometryProxy) -> Int { p.reservedRegions(kind: .division).count }", "27.1"),
    ("UIView.reservedRegions", "import UIKit\n@MainActor func f(v: UIView) -> Int { v.reservedRegions(kind: .division, options: .includeInactive).count }", "27.1"),
    ("ArrangementView", "import SwiftUI\nstruct V: View { var body: some View { ArrangementView { Text(\"a\") } secondary: { Text(\"b\") } } }", "27.1"),
    ("UIArrangementViewController", "import UIKit\n@MainActor func f() { _ = UIArrangementViewController() }", "27.1"),
    ("toolbarVerticalBehavior", "import SwiftUI\nfunc f(v: some View) -> some View { v.toolbarVerticalBehavior(.disabled) }", "27.1"),
    ("toolbarVerticalCompressionBehavior", "import SwiftUI\nfunc f(v: some View) -> some View { v.toolbarVerticalCompressionBehavior(.prefersToolbarItems) }", "27.1"),
    ("toolbarVerticalEdge", "import SwiftUI\nfunc f(e: EnvironmentValues) -> HorizontalEdge? { e.toolbarVerticalEdge }", "27.1"),
    ("ToolbarContent.axisBehavior", "import SwiftUI\nfunc f(c: some ToolbarContent) -> some ToolbarContent { c.axisBehavior(.verticalPreferred) }", "27.1"),
    ("UIBarButtonItem.axisBehavior", "import UIKit\n@MainActor func f(i: UIBarButtonItem) { i.axisBehavior = .horizontalOnly }", "27.1"),
    ("preferredVerticalBarBehavior", "import UIKit\nfinal class C: UIViewController { override var preferredVerticalBarBehavior: UIVerticalBarBehavior { .disabled } }", "27.1"),
    ("verticalBarCompressionBehavior", "import UIKit\n@MainActor func f(n: UINavigationItem) { n.verticalBarCompressionBehavior = .prefersBarItems }", "27.1"),
    ("UIView.LayoutRegion.bar", "import UIKit\n@MainActor func f(v: UIView) { _ = v.layoutGuide(for: .bar(onEdge: NSDirectionalRectEdge.trailing, extent: 44)) }", "27.1"),
    ("CameraCaptureAccessory", "import SwiftUI\nfunc f() { _ = CameraCaptureAccessory { Text(\"t\") } }", "27.1"),
    ("UISceneAccessory.cameraCapture", "import UIKit\n@MainActor func f() { _ = UISceneAccessory.cameraCapture(sceneConfiguration: UISceneConfiguration()) }", "27.1"),
    ("builtInInnerUltraWideCamera", "import AVFoundation\nfunc f() -> AVCaptureDevice.DeviceType { .builtInInnerUltraWideCamera }", "27.1"),
    ("AVCaptureDeviceDirectionCoordinator", "import AVKit\nimport UIKit\n@MainActor func f(v: UIView) { _ = AVCaptureDeviceDirectionCoordinator(view: v, deviceTypes: []) }", "27.1"),
    ("ContentMarginGuide", "import SwiftUI\nfunc f(v: some View) -> some View { v.contentMargins(for: .container) }", "27.1"),
    ("presentationPlacement", "import SwiftUI\nfunc f(v: some View) -> some View { v.presentationPlacement(.trailing) }", "27.0"),
    ("defaultTabBarPlacement", "import SwiftUI\nfunc f(v: some View) -> some View { v.defaultTabBarPlacement(.sidebar) }", "27.0"),
    ("UITabBarControllerSidebar.preferredPlacement", "import UIKit\n@MainActor func f(t: UITabBarController) { t.sidebar.preferredPlacement = .sidebar }", "27.0"),
    ("UISheetPresentationController.preferredPlacement", "import UIKit\n@MainActor func f(s: UISheetPresentationController) { s.preferredPlacement = .trailing }", "27.0"),
    ("dynamicAspectRatio", "import AVFoundation\nfunc f(d: AVCaptureDevice) -> AVCaptureDevice.AspectRatio? { d.dynamicAspectRatio }", "26.0"),
    ("isCameraSensorOrientationCompensationEnabled", "import AVFoundation\nfunc f(o: AVCapturePhotoOutput) { o.isCameraSensorOrientationCompensationEnabled = false }", "26.0"),
]


def previous(version):
    return {"27.1": "27.0", "27.0": "26.0", "26.0": "18.0", "15.0": "14.0"}[version]


def check_gates():
    s = "gates"
    for name, src, version in GATED:
        below = previous(version)
        rc, diags, err = compile_ios(src + "\n", target=below, sil=False)
        ok = rc != 0 and any(f"only available in iOS {version} or newer" in m for _, m in diags)
        if ok:
            rc2, diags2, err2 = compile_ios(src + "\n", target=version, sil=False)
            ok = rc2 == 0
            err = err2 if not ok else err
        report(s, f"{name} requires iOS {version}", ok, err)


# ---------------------------------------------------------------- names

def check_names():
    s = "names"
    expect_diag(s, "toolbarCompressionBehavior (talk name) does not exist",
                "import SwiftUI\nfunc f(v: some View) -> some View { v.toolbarCompressionBehavior(.prefersTabBar) }\n",
                ["has no member 'toolbarCompressionBehavior'"])
    expect_diag(s, "UIWindowSceneActivationAction is spelled UIWindowScene.ActivationAction in Swift",
                "import UIKit\n@MainActor func f() { _ = UIWindowSceneActivationAction(alternate: nil) { _ in nil } }\n",
                ["has been renamed to 'UIWindowScene.ActivationAction'"])
    expect_diag(s, "handleHingeUnavailable is not an API",
                "import UIKit\n@MainActor func f() { handleHingeUnavailable() }\n",
                ["cannot find 'handleHingeUnavailable' in scope"])
    expect_diag(s, "leftItemSupplementsBackButton is spelled leftItemsSupplementBackButton",
                "import UIKit\n@MainActor func f(n: UINavigationItem) { n.leftItemSupplementsBackButton = false }\n",
                ["has no member 'leftItemSupplementsBackButton'"])
    pitfall = ('import UIKit\n@MainActor func f() -> UIAction {\n'
               '    UIWindowScene.ActivationAction(title: "New") { _ in\n'
               '        UIWindowScene.ActivationConfiguration(userActivity: NSUserActivity(activityType: "a"))\n'
               '    }\n}\n')
    expect_diag(s, "ActivationAction(title:) with a void closure binds to the unsupported handler initializer",
                pitfall, ["result of 'UIWindowScene.ActivationConfiguration' initializer is unused"], severity="warning")
    expect_clean(s, "ActivationAction(title:alternate:) { } binds to the configuration provider",
                 pitfall.replace('(title: "New")', '(title: "New", alternate: nil)'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip", action="append", default=[], choices=["snippets", "gates", "names"])
    args = parser.parse_args()
    global SDK
    SDK = run(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"]).stdout.strip()
    check_toolchain()
    check_sdk()
    for section, fn in [("snippets", check_snippets), ("gates", check_gates), ("names", check_names)]:
        if section not in args.skip:
            fn()
    failed = RESULTS.count(False)
    print(f"\n{len(RESULTS) - failed} passed, {failed} failed")
    if failed:
        print(f"probe files kept in {WORK}")
    else:
        shutil.rmtree(WORK, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
