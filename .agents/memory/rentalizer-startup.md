---
name: Rentalizer startup quirks
description: What's needed to run the 08-rentalizer FastAPI app on Replit (libgomp, TemplateResponse API, auth fix)
---

## Rules

1. **LD_LIBRARY_PATH must include GCC libs** — LightGBM needs `libgomp.so.1` which isn't on the default path. The workflow command must prefix: `LD_LIBRARY_PATH=/nix/store/bmi5znnqk4kg2grkrhk6py0irc8phf6l-gcc-14.2.1.20250322-lib/lib:$LD_LIBRARY_PATH`

**Why:** LightGBM's pre-built wheel links against libgomp but Nix doesn't expose it in the default LD path. `gcc -print-file-name=libgomp.so.1` reveals the path.

2. **Starlette TemplateResponse new signature** — newer Starlette (bundled with FastAPI 0.139+) requires `TemplateResponse(request=request, name="index.html")` not the old dict form `TemplateResponse("index.html", {"request": request})`.

**Why:** Passing the context as a positional dict triggers an "unhashable type: dict" error in Jinja2's template cache.

3. **Auth dependency must raise HTTPException, not JSONResponse** — `raise JSONResponse(...)` throws a TypeError at runtime because JSONResponse is not an exception. Use `raise HTTPException(status_code=401, detail="...")` instead.

**How to apply:** Any FastAPI dependency that wants to return an HTTP error must use HTTPException (or a subclass), never raise a Response object directly.

4. **pytest is listed in requirements.txt but NOT installed in the env, and there is no `pip`.** Install dev deps with `uv pip install "pytest==9.1.1"`. Run the suite with the same libgomp `LD_LIBRARY_PATH` prefix as the workflow (model-loading tests need it); tests that call `load_model()` should `pytest.skip` on `ModelNotReadyError` so a missing native lib doesn't look like a code failure. Tests import via `from src... import`, which needs a root `conftest.py` inserting the package dir onto `sys.path`.
