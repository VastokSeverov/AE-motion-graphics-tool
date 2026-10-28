/* VASTOCHNIY AE Copilot — only the local still-image background-removal action. */
var Vasto = Vasto || {};

Vasto.getSelectedImageInfo = function () {
    try {
        if (!app.project || !(app.project.activeItem instanceof CompItem)) {
            throw new Error('Open a composition and select one still image layer first.');
        }
        var comp = app.project.activeItem;
        if (!comp.selectedLayers || comp.selectedLayers.length !== 1) {
            throw new Error('Select exactly one still image layer.');
        }
        var layer = comp.selectedLayers[0];
        if (!(layer instanceof AVLayer) || !layer.source || !layer.source.mainSource || !layer.source.mainSource.file) {
            throw new Error('Selected layer must be a saved local still image—not text, a shape, video, or a generated solid.');
        }
        var file = layer.source.mainSource.file;
        var ext = file.name.toLowerCase().split('.').pop();
        if (!({png:1,jpg:1,jpeg:1,webp:1,tif:1,tiff:1,bmp:1}[ext])) {
            throw new Error('Supported formats: PNG, JPG/JPEG, WEBP, TIFF, and BMP. Video is not supported yet.');
        }
        if (!file.exists) throw new Error('The source image file is missing or offline.');
        return JSON.stringify({path:file.fsName, name:layer.name});
    } catch (e) {
        return JSON.stringify({error:e.toString()});
    }
};

Vasto.replaceSelectedImageSource = function (outputPath, expectedSourcePath) {
    var undoStarted = false;
    var importedFootage = null;
    try {
        if (!app.project || !(app.project.activeItem instanceof CompItem)) {
            throw new Error('Active composition changed. Transparent PNG was saved, but the layer was not changed.');
        }
        var comp = app.project.activeItem;
        if (!comp.selectedLayers || comp.selectedLayers.length !== 1) {
            throw new Error('Selection changed. Transparent PNG was saved, but the layer was not changed.');
        }
        var layer = comp.selectedLayers[0];
        if (!(layer instanceof AVLayer) || !layer.source || !layer.source.mainSource || !layer.source.mainSource.file) {
            throw new Error('Selected layer is no longer the original image. Transparent PNG was saved, but the layer was not changed.');
        }
        if (layer.source.mainSource.file.fsName !== expectedSourcePath) {
            throw new Error('Selected image changed during processing. Transparent PNG was saved, but the layer was not changed.');
        }
        var outputFile = new File(outputPath);
        if (!outputFile.exists) throw new Error('Transparent PNG was not found: ' + outputPath);
        app.beginUndoGroup('VASTOCHNIY — Remove Background'); undoStarted = true;
        importedFootage = app.project.importFile(new ImportOptions(outputFile));
        layer.replaceSource(importedFootage, false);
        app.endUndoGroup(); undoStarted = false;
        return JSON.stringify({message:'SUCCESS: Background removed. The layer now uses a transparent PNG; Undo restores the original source.'});
    } catch (e) {
        if (undoStarted) { try { app.endUndoGroup(); } catch (ignore) {} }
        return JSON.stringify({error:'ERROR: ' + e.toString()});
    }
};
