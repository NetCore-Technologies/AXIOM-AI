diff --git a/axiom/api/model_paths.py b/axiom/api/model_paths.py
index 656c8b6..2091e38 100644
--- a/axiom/api/model_paths.py
+++ b/axiom/api/model_paths.py
@@ -50,11 +50,10 @@ def _inside(candidate: str, roots: Iterable[Path]) -> Path:
     candidate_real = os.path.realpath(candidate)
     for root in roots:
         root_real = os.path.realpath(os.fspath(root))
-        try:
-            if os.path.commonpath((candidate_real, root_real)) == root_real:
-                return Path(candidate_real)
-        except ValueError:
-            continue
+        if candidate_real == root_real or candidate_real.startswith(
+            root_real + os.sep
+        ):
+            return Path(candidate_real)
     raise ValueError("path is outside an AXIOM trusted filesystem boundary")
 
 
@@ -75,11 +74,8 @@ def validate_child_path(
     parent_real = os.path.realpath(_coerce_path(parent))
     child_raw = _coerce_path(child)
     candidate = os.path.realpath(os.path.join(parent_real, child_raw))
-    try:
-        if os.path.commonpath((candidate, parent_real)) != parent_real:
-            raise ValueError("child path escapes its trusted parent")
-    except ValueError as exc:
-        raise ValueError("child path escapes its trusted parent") from exc
+    if candidate != parent_real and not candidate.startswith(parent_real + os.sep):
+        raise ValueError("child path escapes its trusted parent")
     return Path(candidate)
 
 # Backwards-compatible default root; caller-supplied paths must still be validated.
diff --git a/axiom/optimizer/model.py b/axiom/optimizer/model.py
index 63ee13a..b358473 100644
--- a/axiom/optimizer/model.py
+++ b/axiom/optimizer/model.py
@@ -117,10 +117,9 @@ def _config(path: Path) -> dict[str, Any]:
     trusted_path = validate_model_path(path)
     root_str = os.path.realpath(trusted_path)
     model_root_real = os.path.realpath(MODEL_ROOT)
-    try:
-        if os.path.commonpath((root_str, model_root_real)) != model_root_real:
-            return {}
-    except ValueError:
+    if root_str != model_root_real and not root_str.startswith(
+        model_root_real + os.sep
+    ):
         return {}
     if not os.path.isdir(root_str):
         return {}
