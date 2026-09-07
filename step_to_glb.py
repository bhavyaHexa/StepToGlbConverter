from pathlib import Path
from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.XCAFApp import XCAFApp_Application
from OCC.Core.XCAFDoc import XCAFDoc_DocumentTool
from OCC.Core.TDF import TDF_LabelSequence
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.RWGltf import RWGltf_CafWriter
from OCC.Core.RWMesh import RWMesh_NameFormat_Product
from OCC.Core.TColStd import TColStd_IndexedDataMapOfStringString
from OCC.Core.Message import Message_ProgressRange
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.Interface import Interface_Static

# Force OCCT to interpret all STEP geometry in millimeters.
Interface_Static.SetCVal("xstep.cascade.unit", "MM")

# ---- Folder locations ----
BASE_DIR = Path(__file__).parent
STEP_DIR = BASE_DIR / "STEP" / "PL" / "Female Wiggins" 
GLB_DIR  = BASE_DIR / "GLB" / "PL" / "Female Wiggins"

# ---- Mesh quality ----
DEFLECTION_FACTOR  = 0.12
ANGULAR_DEFLECTION = 0.02   # radians

def get_bbox_diagonal(shape) -> float:
    """Calculate bounding box diagonal length for adaptive deflection."""
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    dx, dy, dz = xmax - xmin, ymax - ymin, zmax - zmin
    return (dx**2 + dy**2 + dz**2) ** 0.5


def step_to_glb(step_path: str, glb_path: str) -> bool:
    """
    Convert a STEP file to GLB preserving assembly structure, product names,
    and individual meshes. No mesh merging or compound flattening performed.
    """
    app = XCAFApp_Application.GetApplication()
    doc = TDocStd_Document("MDTV-XCAF")
    app.NewDocument("MDTV-XCAF", doc)

    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetNameMode(True)
    reader.SetLayerMode(True)
    reader.SetPropsMode(True)

    if reader.ReadFile(step_path) != IFSelect_RetDone:
        print(f"  ERROR: Could not read STEP file '{step_path}'.")
        return False
    if not reader.Transfer(doc):
        print(f"  ERROR: Transfer failed for '{step_path}'.")
        return False

    shape_tool = XCAFDoc_DocumentTool.ShapeTool(doc.Main())
    labels = TDF_LabelSequence()
    shape_tool.GetFreeShapes(labels)

    # --- Tessellate each shape ---
    for i in range(labels.Length()):
        shape = shape_tool.GetShape(labels.Value(i + 1))
        if not shape.IsNull():
            diag = get_bbox_diagonal(shape)
            lin_defl = max(diag * DEFLECTION_FACTOR, 1e-6)
            BRepMesh_IncrementalMesh(
                shape, lin_defl, False, ANGULAR_DEFLECTION, True
            ).Perform()

    # --- Export GLB with product names ---
    writer = RWGltf_CafWriter(glb_path, True)
    writer.SetTransformationFormat(0)  # Compact
    writer.ChangeCoordinateSystemConverter().SetInputLengthUnit(0.001)  # MM to Meters
    writer.SetNodeNameFormat(RWMesh_NameFormat_Product)

    ok = writer.Perform(
        doc, labels, None,
        TColStd_IndexedDataMapOfStringString(), Message_ProgressRange()
    )

    return ok


def batch_convert():
    GLB_DIR.mkdir(parents=True, exist_ok=True)

    step_files = []
    for ext in ("*.step", "*.stp", "*.STEP", "*.STP"):
        step_files.extend(STEP_DIR.glob(ext))
    
    # Deduplicate while preserving order
    seen = set()
    unique_step_files = []
    for f in step_files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_step_files.append(f)
    step_files = sorted(unique_step_files)

    if not step_files:
        print(f"No .step / .stp files found in {STEP_DIR}")
        return

    total_files = len(step_files)
    print(f"Total number of detected STEP files: {total_files}")
    print(f"Found {total_files} STEP file(s) in {STEP_DIR}\n")

    for i, step_file in enumerate(step_files, start=1):
        glb_file = GLB_DIR / (step_file.stem + ".glb")
        print(f"Converting ({i}/{total_files}): {step_file.name} -> {glb_file.name}")
        success = step_to_glb(str(step_file), str(glb_file))
        status = "OK" if success else "FAILED"
        print(f"  [{status}]\n")

    print("Step 1 Complete: STEP files converted to GLB.")


if __name__ == "__main__":
    batch_convert()
