// Builds a Photoshop template for one tip cup sticker, sized for Cricut Print Then Cut.
//
// Run it in Photoshop with File > Scripts > Browse... It saves next to this script:
//   sticker_template.psd          - put your design inside the "Sticker" group; the group is
//                                   masked to the cut shape, so anything you add is trimmed to it
//   sticker_template_preview.png  - what the empty template looks like, for the README
//
// Every recess on the cup and lid is 40 x 30 mm with 4 mm corners. The sticker is 1 mm smaller
// all round so Cricut's cut tolerance still leaves it inside the recess.
#target photoshop

var STICKER_W_MM = 38;
var STICKER_H_MM = 28;
var CORNER_R_MM = 3;   // concentric with the recess's 4 mm corners
var SAFE_MM = 2;       // keep text and faces inside this margin
var DPI = 300;

function cTID(s) { return charIDToTypeID(s); }

function px(mm) { return mm / 25.4 * DPI; }

function pathPoint(anchor, inDir, outDir) {
    var p = new PathPointInfo();
    p.kind = PointKind.CORNERPOINT;
    p.anchor = anchor;
    p.leftDirection = outDir;   // Photoshop's "left" handle is the one toward the next point
    p.rightDirection = inDir;
    return p;
}

// Selects a rounded rectangle inset from the canvas edges (all values in pixels).
// Built from a temporary path because the radius on a plain rectangle selection is
// ignored by current Photoshop versions.
function selectRoundedRect(inset, radius) {
    var doc = app.activeDocument;
    var s = 72 / doc.resolution;   // path coordinates are in points, not pixels
    var l = inset * s, t = inset * s, r = radius * s, k = r * 0.5523;
    var rt = (doc.width.as("px") - inset) * s, b = (doc.height.as("px") - inset) * s;
    var pts = [
        pathPoint([l + r, t], [l + r - k, t], [l + r, t]),
        pathPoint([rt - r, t], [rt - r, t], [rt - r + k, t]),
        pathPoint([rt, t + r], [rt, t + r - k], [rt, t + r]),
        pathPoint([rt, b - r], [rt, b - r], [rt, b - r + k]),
        pathPoint([rt - r, b], [rt - r + k, b], [rt - r, b]),
        pathPoint([l + r, b], [l + r, b], [l + r - k, b]),
        pathPoint([l, b - r], [l, b - r + k], [l, b - r]),
        pathPoint([l, t + r], [l, t + r], [l, t + r - k])
    ];
    var sub = new SubPathInfo();
    sub.closed = true;
    sub.operation = ShapeOperation.SHAPEADD;
    sub.entireSubPath = pts;
    var path = doc.pathItems.add("rounded-rect", [sub]);
    path.makeSelection(0, true, SelectionType.REPLACE);
    path.remove();
}

function addLayerMaskFromSelection() {
    var ref = new ActionReference();
    ref.putEnumerated(cTID("Chnl"), cTID("Chnl"), cTID("Msk "));
    var desc = new ActionDescriptor();
    desc.putClass(cTID("Nw  "), cTID("Chnl"));
    desc.putReference(cTID("At  "), ref);
    desc.putEnumerated(cTID("Usng"), cTID("UsrM"), cTID("RvlS"));
    executeAction(cTID("Mk  "), desc, DialogModes.NO);
}

function rgb(r, g, b) {
    var c = new SolidColor();
    c.rgb.red = r;
    c.rgb.green = g;
    c.rgb.blue = b;
    return c;
}

function buildTemplate(outFolder) {
    var w = Math.round(px(STICKER_W_MM));
    var h = Math.round(px(STICKER_H_MM));
    var safe = px(SAFE_MM);
    var doc = app.documents.add(w, h, DPI, "sticker_template", NewDocumentMode.RGB,
                                DocumentFill.TRANSPARENT);
    var starter = doc.activeLayer;

    // Everything inside this group is masked to the sticker's cut shape.
    var group = doc.layerSets.add();
    group.name = "Sticker (design inside this group)";
    var base = group.artLayers.add();
    base.name = "Background colour";
    doc.selection.selectAll();
    doc.selection.fill(rgb(255, 255, 255));
    doc.selection.deselect();
    var design = group.artLayers.add();
    design.name = "Your design (place artwork here)";

    doc.activeLayer = group;
    selectRoundedRect(0, px(CORNER_R_MM));
    addLayerMaskFromSelection();
    doc.selection.deselect();

    // Safe-area outline, outside the group so it never prints.
    doc.activeLayer = group;
    var guide = doc.artLayers.add();
    guide.name = "GUIDE: safe area (hide before export)";
    guide.move(doc, ElementPlacement.PLACEATBEGINNING);
    selectRoundedRect(safe, Math.max(px(CORNER_R_MM - SAFE_MM), 1));
    doc.selection.stroke(rgb(255, 0, 170), 2, StrokeLocation.CENTER);
    doc.selection.deselect();
    starter.remove();

    doc.guides.add(Direction.VERTICAL, UnitValue(safe, "px"));
    doc.guides.add(Direction.VERTICAL, UnitValue(w - safe, "px"));
    doc.guides.add(Direction.VERTICAL, UnitValue(w / 2, "px"));
    doc.guides.add(Direction.HORIZONTAL, UnitValue(safe, "px"));
    doc.guides.add(Direction.HORIZONTAL, UnitValue(h - safe, "px"));
    doc.guides.add(Direction.HORIZONTAL, UnitValue(h / 2, "px"));

    doc.activeLayer = design;   // so File > Place lands inside the group
    var psd = new PhotoshopSaveOptions();
    psd.layers = true;
    psd.embedColorProfile = true;
    doc.saveAs(new File(outFolder + "/sticker_template.psd"), psd, false);
    var png = new PNGSaveOptions();
    png.compression = 9;
    doc.saveAs(new File(outFolder + "/sticker_template_preview.png"), png, true);
    return doc;
}

(function () {
    var units = app.preferences.rulerUnits;
    var dialogs = app.displayDialogs;
    app.preferences.rulerUnits = Units.PIXELS;
    app.displayDialogs = DialogModes.NO;
    try {
        buildTemplate(File($.fileName).parent.fsName);
    } finally {
        app.preferences.rulerUnits = units;
        app.displayDialogs = dialogs;
    }
})();
