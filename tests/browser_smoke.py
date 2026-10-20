"""Exercise the standalone viewer; run with `uv run --with playwright python tests/browser_smoke.py`."""

from __future__ import annotations

import argparse
import functools
import gzip
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/browser-check")
    parser.add_argument("--site", type=Path, default=ROOT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((args.site / "data/catalog.json").read_text())["scenes"]
    handler = functools.partial(QuietHandler, directory=str(args.site.resolve()))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}"
    errors, external, requests, loaded = [], [], [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
            context = browser.new_context(viewport={"width": 1440, "height": 1000})

            def route(request_route):
                requested = request_route.request.url
                if urlsplit(requested).netloc != urlsplit(url).netloc:
                    external.append(requested)
                    request_route.abort()
                else:
                    requests.append(requested)
                    request_route.continue_()

            context.route("**/*", route)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.goto(url, wait_until="domcontentloaded")
            for entry in catalog:
                page.select_option("#sceneSelect", entry["id"])
                page.wait_for_function("document.body.dataset.ready === 'true'", timeout=60000)
                page.wait_for_function("expected => document.getElementById('title').textContent === expected",
                                       arg=entry["title"], timeout=60000)
                assert page.locator("canvas").count() == 1
                assert f"{entry['ct_slices']} CT slices" in page.locator("#stats").inner_text()
                loaded.append(entry["id"])
                print("Loaded", entry["id"], flush=True)
            for button in ["vTop", "vFront", "vSide", "vFocus", "vFit"]:
                page.locator(f"#{button}").click()
            for color in ["z", "r", "angle"]:
                page.select_option("#gCol", color)
            for control in ["sZ", "rMax", "zMin", "pSize", "sOp"]:
                page.locator(f"#{control}").evaluate("""e => {
                  e.value = (+e.min + +e.max) / 2; e.dispatchEvent(new Event('input', {bubbles:true}));
                }""")
            for control in ["sClip", "gOn", "sOn", "tOn", "envOn"]:
                page.locator(f"#{control}").uncheck()
                page.locator(f"#{control}").check()
            page.select_option("#sceneSelect", "PHerc0175A")
            page.wait_for_function("document.body.dataset.ready === 'true'")
            page.mouse.move(530, 400)
            page.mouse.down()
            page.mouse.move(650, 450, steps=15)
            page.mouse.up()
            page.wait_for_timeout(300)
            page.screenshot(path=str(args.output / "desktop.png"))

            invalid = args.output / "invalid.json"
            invalid.write_text('{"unsupported":true}')
            page.locator("#sceneFile").set_input_files(invalid)
            page.wait_for_function("document.body.dataset.ready === 'error'")
            assert "Unsupported scene format" in page.locator("#loading").inner_text()

            source = args.site / catalog[-1]["scene"]
            with gzip.open(source, "rt") as stream:
                custom = json.load(stream)
            custom["title"] = 'CT <img src=x onerror="window.sceneInjected=true">'
            imported = args.output / "import.json.gz"
            with gzip.open(imported, "wt") as stream:
                json.dump(custom, stream)
            page.locator("#sceneFile").set_input_files(imported)
            page.wait_for_function("document.body.dataset.ready === 'true'")
            assert page.locator("#title").inner_text() == custom["title"]
            assert page.locator("#title img").count() == 0
            assert page.evaluate("window.sceneInjected") is None
            assert page.locator("canvas").count() == 1
            custom.update(title="Empty center scene", points_b64="", points_total=0, slices=[], envelope=[])
            empty = args.output / "empty.json"
            empty.write_text(json.dumps(custom))
            page.locator("#sceneFile").set_input_files(empty)
            page.wait_for_function("document.body.dataset.ready === 'true'")
            assert "0 CT slices" in page.locator("#stats").inner_text()

            page.set_viewport_size({"width": 390, "height": 844})
            page.select_option("#sceneSelect", "PHerc0191")
            page.wait_for_function("document.body.dataset.ready === 'true'")
            page.wait_for_timeout(300)
            page.screenshot(path=str(args.output / "narrow.png"))
            assert page.locator("#panel").evaluate("e => e.clientWidth") <= 390
            report = {"browser": browser.version, "loaded_scenes": loaded, "errors": errors,
                      "external_requests": external, "local_requests": len(requests),
                      "controls": "passed", "file_import": "passed", "invalid_import": "passed",
                      "empty_scene": "passed", "narrow_layout": "passed"}
            (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            browser.close()
            assert not errors, errors
            assert not external, external
            print(json.dumps(report, indent=2))
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


if __name__ == "__main__":
    main()
