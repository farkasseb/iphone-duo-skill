# iPhone Duo Skill

An agent skill for the foldable iPhone Duo. It covers the iOS 27.1 SDK APIs and the behaviors that differ from other iPhones:

- the vertical side bar
- custom chrome beside it
- the fold, as reserved regions and arrangements
- the hinge
- content on the outer display
- the two front cameras
- testing poses in the simulator

It follows the [Agent Skills](https://agentskills.io) format and works with any agent that loads `SKILL.md` skills, including Claude Code and OpenAI Codex CLI.

It deliberately leaves general resizing to Apple's **app-resizability** skill, which ships with Xcode 27.1. That skill covers `UIScreen.main`, orientation and idiom checks, scene lifecycle, and safe areas, including `verticalBarEdge` and `toolbarVerticalEdge`. A request to "get my app ready for iPhone Duo" should start there; this skill adds what that one doesn't cover.

## Why it exists

iPhone Duo and its APIs shipped with iOS 27.1 in October 2026, after most models' training data:

- Bars move to a vertical side bar, but only for container-managed bars in apps rebuilt with the 27.1 SDK. New modifiers control the axis, compression and opt-out.
- The fold is a reserved region. Two-view layouts can split at it with `ArrangementView`.
- The hinge has its own APIs, meant for interactions rather than layout.
- Only camera apps can show UI on both displays, through a camera capture scene accessory.
- A virtual front camera follows the active display, and a new coordinator reports which way each camera faces.
- Several names in Apple's talks differ from the SDK.

## Installation

Copy or clone the directory into your agent's skills folder:

```bash
# Claude Code
git clone https://github.com/farkasseb/iphone-duo-skill ~/.claude/skills/iphone-duo

# Codex CLI
git clone https://github.com/farkasseb/iphone-duo-skill ~/.agents/skills/iphone-duo
```

Agents load only `SKILL.md` and read `references/` on demand. `evals/` and `tests/` are optional.

## Layout

```
SKILL.md                            scope, SDK gates, practical decisions and reference routing
agents/openai.yaml                  Codex UI metadata and invocation policy
references/bars-and-fold.md         vertical bars, custom chrome, content margins, reserved regions, arrangements, hinge
references/displays-and-camera.md   apps by linked SDK, orientation, scenes and split view, scene accessories, cameras, simulator testing
evals/                              benchmark prompts with graded expectations
tests/                              compile probes (run.sh, probes.py)
```

## Verification

`tests/run.sh` checks the Swift examples and API availability against an installed Xcode with the iOS 27.1 SDK or later. Runtime observations require separate simulator or device checks. It uses `$XCODE` (an `.app` path), then `$DEVELOPER_DIR`, then the `xcode-select` default.

```bash
XCODE=/path/to/Xcode-27.1.app tests/run.sh
```

It checks:

- **sdk:** the selected iOS SDK declares the iPhone Duo APIs.
- **snippets:** every Swift block in `SKILL.md` and `references/` compiles with no warnings (`swiftc -emit-sil`, Swift 6 mode, iOS SDK). A new block without a probe fails the run.
- **gates:** each API fails one release below the version the skill states and compiles at that version.
- **names:** names used in Apple's talks that differ from the SDK keep failing. The `UIWindowScene.ActivationAction` trailing-closure pitfall still behaves as described.

Last run, 2026-11-02: Xcode 27.2 (27B52), iOS 27.2 SDK, Swift 6.4.2 (swiftlang-6.4.2.1.9): 69 passed.

Runtime guidance was rechecked on iOS 27.1 simulator build 24A94401 with mobilecli 1.0.17, using isolated simulators and fresh builds, with an iPhone 17 Pro on iOS 27.2 as the nonfoldable comparison. Linked-SDK probes used SDKs 26.5, 27.0 and 27.1 on that same runtime. The audit covered system and custom toolbars, compression, RTL fold avoidance with same-size updates, arrangements, system presentations, hinge paths, orientation/full-screen policies, new scenes and camera accessory availability/presentation. On 2026-10-25 an iPhone Duo simulator also booted on the Duo-only iOS 27.2 runtime (24B91014); the guidance was not re-audited there.

The recheck corrected earlier simulator conclusions: compression preferences worked; the division frame included its margins; camera accessories actually presented without capture. Other observations remain qualified in the references. The simulator did not establish real capture behavior, open-portrait/laptop layout or hardware-only conditions. The runnable fixtures, paired-display captures, logs and initial failures were preserved separately with the review; they are not a new test framework in this skill.

## Evals

`evals/evals.json` has 11 prompts with graded expectations:

- facts about the iOS 27.1 bar, fold, hinge, scene-accessory and camera APIs
- toolchain choice
- one routing case, where generic resizing work should go to app-resizability

Use the few prompts relevant to a change. For a qualitative with/without-skill spot check, disable external references only during that check, preserve both answers, and compile code against the selected SDK. The existing-working-toolbar prompt guards against unnecessary changes. A spot check is not a broad benchmark score.

## Sources

- Apple tech talks (October 2026):
  - [Design for iPhone Duo](https://developer.apple.com/videos/play/tech-talks/111466/)
  - [Prepare your app for iPhone Duo](https://developer.apple.com/videos/play/tech-talks/111461/)
  - [Raise the bar with iPhone Duo](https://developer.apple.com/videos/play/tech-talks/111462/)
  - [Strike a pose with adaptive layouts on iPhone Duo](https://developer.apple.com/videos/play/tech-talks/111463/)
  - [Leverage multiple displays and scenes on iPhone Duo](https://developer.apple.com/videos/play/tech-talks/111464/)
  - [Build a great camera experience for iPhone Duo](https://developer.apple.com/videos/play/tech-talks/111465/)
- iPhone Duo group labs: [285](https://developer.apple.com/videos/play/meet-with-apple/285/) and [286](https://developer.apple.com/videos/play/meet-with-apple/286/)
- Apple documentation:
  - [Choosing a camera by the direction it faces](https://developer.apple.com/documentation/avkit/choosing-a-camera-by-the-direction-it-faces)
  - [AVCaptureDeviceDirectionCoordinator](https://developer.apple.com/documentation/avkit/avcapturedevicedirectioncoordinator)
  - [UIHingeInteraction](https://developer.apple.com/documentation/uikit/uihingeinteraction)
  - [UIViewReservedRegion](https://developer.apple.com/documentation/uikit/uiviewreservedregion)
  - [ReservedRegion](https://developer.apple.com/documentation/swiftui/reservedregion)
  - [ArrangementView](https://developer.apple.com/documentation/swiftui/arrangementview)
  - [UIArrangementViewController](https://developer.apple.com/documentation/uikit/uiarrangementviewcontroller)
  - [toolbarVerticalBehavior(_:)](https://developer.apple.com/documentation/swiftui/view/toolbarverticalbehavior(_:))
  - [preferredVerticalBarBehavior](https://developer.apple.com/documentation/uikit/uiviewcontroller/preferredverticalbarbehavior)
  - [CameraCaptureAccessory](https://developer.apple.com/documentation/swiftui/cameracaptureaccessory)
  - [Presenting content on a connected display](https://developer.apple.com/documentation/uikit/presenting-content-on-a-connected-display)
- [Xcode 27.1 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27_1-release-notes) and [Xcode 27.2 release notes](https://developer.apple.com/documentation/xcode-release-notes/xcode-27_2-release-notes)
- iOS 27.0, 27.1 and 27.2 SDK headers and Swift interfaces, compared

## Contributing

Corrections and additions are welcome. Include the source for any change in behavior or availability: a talk with its timestamp, a documentation page, a compile probe with the toolchain version, or a device or simulator observation with the OS build.
