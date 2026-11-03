// Builds Photoshop templates for the tip cup stickers, sized for Cricut Print Then Cut.
//
// Run it in Photoshop with File > Scripts > Browse... It saves one PSD per entry in STICKERS
// next to this script. Put your design inside the "Sticker" group; the group is masked to the
// cut shape, so anything you add is trimmed to the rounded corners.
//
// Use the sticker sizes tip_cup.py prints. With the default settings the cup's recesses are
// 27 x 36 mm and the lid's are 24 x 32 mm, all with 4 mm corners. Each sticker is 1 mm smaller
// all round so Cricut's cut tolerance still leaves it inside the recess.
#target photoshop

var STICKERS = [
    { name: "sticker_cup", w: 25, h: 34 },
    { name: "sticker_lid", w: 22, h: 30 }
];
var CORNER_R_MM = 3;   // concentric with the recess's 4 mm corners
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

// Selects the whole canvas with rounded corners (radius in pixels). Built from a temporary
// path because the radius on a plain rectangle selection is ignored by current Photoshop
// versions.
function selectRoundedRect(radius) {
    var doc = app.activeDocument;
    var s = 72 / doc.resolution;   // path coordinates are in points, not pixels
    var l = 0, t = 0, r = radius * s, k = r * 0.5523;
    var rt = doc.width.as("px") * s, b = doc.height.as("px") * s;
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

function buildTemplate(outFolder, sticker) {
    var w = Math.round(px(sticker.w));
    var h = Math.round(px(sticker.h));
    var doc = app.documents.add(w, h, DPI, sticker.name, NewDocumentMode.RGB,
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
    selectRoundedRect(px(CORNER_R_MM));
    addLayerMaskFromSelection();
    doc.selection.deselect();
    starter.remove();

    doc.activeLayer = design;   // so File > Place lands inside the group
    var psd = new PhotoshopSaveOptions();
    psd.layers = true;
    psd.embedColorProfile = true;
    doc.saveAs(new File(outFolder + "/" + sticker.name + ".psd"), psd, false);
    return doc;
}

(function () {
    var units = app.preferences.rulerUnits;
    var dialogs = app.displayDialogs;
    app.preferences.rulerUnits = Units.PIXELS;
    app.displayDialogs = DialogModes.NO;
    try {
        for (var i = 0; i < STICKERS.length; i++) {
            buildTemplate(File($.fileName).parent.fsName, STICKERS[i]);
        }
    } finally {
        app.preferences.rulerUnits = units;
        app.displayDialogs = dialogs;
    }
})();
