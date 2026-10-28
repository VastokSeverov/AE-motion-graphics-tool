/* VASTOCHNIY AE Copilot — real After Effects host operations (ExtendScript). */
var Vasto = Vasto || {};
Vasto.executeCommand = function(raw) {
    var cmd;
    try { cmd = eval('(' + raw + ')'); } catch (e) { return JSON.stringify({message:'ERROR: Could not parse command: ' + e.toString()}); }
    try {
        if (!app.project) app.newProject();
        var comp = app.project.activeItem;
        if (!(comp instanceof CompItem)) {
            comp = app.project.items.addComp('VASTOCHNIY_Copilot_Comp', 1080, 1920, 1, 10, 30);
        }
        app.beginUndoGroup('VASTOCHNIY AI Copilot — ' + cmd.action);
        var layer, message;
        if (cmd.action === 'animated_text') {
            layer = comp.layers.addText(String(cmd.text || 'VASTOCHNIY'));
            layer.name = 'AI — ' + String(cmd.text || 'VASTOCHNIY').substring(0,80);
            var textProp = layer.property('ADBE Text Properties').property('ADBE Text Document');
            var doc = textProp.value;
            doc.fontSize = Math.min(140, Math.max(48, 1080 / Math.max(5, String(cmd.text || '').length) * 0.65));
            var textColors = {
                white: [1,1,1], red: [1,0,0], green: [0,0.75,0.15],
                blue: [0.1,0.35,1], yellow: [1,0.85,0], orange: [1,0.35,0],
                purple: [0.55,0.2,0.9], pink: [1,0.25,0.55], black: [0,0,0], cyan: [0,1,1]
            };
            var requestedColor = String(cmd.color || 'white').toLowerCase();
            doc.applyFill = true;
            doc.fillColor = textColors[requestedColor] || textColors.white;
            doc.justification = ParagraphJustification.CENTER_JUSTIFY;
            textProp.setValue(doc);
            layer.property('ADBE Transform Group').property('ADBE Position').setValue([comp.width/2, comp.height/2]);
            var scale = layer.property('ADBE Transform Group').property('ADBE Scale');
            var dur = Math.max(0.2, Math.min(5, Number(cmd.duration) || 0.8));
            scale.setValueAtTime(0,[0,0]); scale.setValueAtTime(dur*0.72,[112,112]); scale.setValueAtTime(dur,[100,100]);
            try { scale.setInterpolationTypeAtKey(1,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER); scale.setInterpolationTypeAtKey(2,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER); scale.setInterpolationTypeAtKey(3,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER); } catch(ignore) {}
            var opacity = layer.property('ADBE Transform Group').property('ADBE Opacity');
            opacity.setValueAtTime(0,0);
            opacity.setValueAtTime(dur,100);
            try {
                opacity.setInterpolationTypeAtKey(1,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
                opacity.setInterpolationTypeAtKey(2,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER);
            } catch(ignoreOpacityEase) {}
            message = 'SUCCESS: Created animated text layer “' + layer.name + '” in ' + comp.name + '.';
        } else if (cmd.action === 'shape') {
            layer = comp.layers.addShape(); layer.name = 'AI — Shape Layer';
            var root = layer.property('ADBE Root Vectors Group'); var group = root.addProperty('ADBE Vector Group'); group.name='Rectangle';
            var rect=group.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect'); rect.property('ADBE Vector Rect Size').setValue([600,260]); rect.property('ADBE Vector Rect Roundness').setValue(28);
            var fill=group.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill'); fill.property('ADBE Vector Fill Color').setValue([0.25,0.65,1]);
            layer.property('ADBE Transform Group').property('ADBE Position').setValue([comp.width/2,comp.height/2]); message='SUCCESS: Created a rounded rectangle shape layer in '+comp.name+'.';
        } else if (cmd.action === 'liquid_glass') {
            layer = comp.layers.addShape(); layer.name='AI — Liquid Glass Starter';
            var rt=layer.property('ADBE Root Vectors Group'); var gr=rt.addProperty('ADBE Vector Group'); gr.name='Glass Capsule';
            var rr=gr.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Rect'); rr.property('ADBE Vector Rect Size').setValue([620,260]); rr.property('ADBE Vector Rect Roundness').setValue(130);
            var gf=gr.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill'); gf.property('ADBE Vector Fill Color').setValue([0.72,0.86,1]); gf.property('ADBE Vector Fill Opacity').setValue(28);
            var stroke=gr.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Stroke'); stroke.property('ADBE Vector Stroke Color').setValue([1,1,1]); stroke.property('ADBE Vector Stroke Opacity').setValue(72); stroke.property('ADBE Vector Stroke Width').setValue(3);
            layer.property('ADBE Transform Group').property('ADBE Position').setValue([comp.width/2,comp.height/2]);
            try { layer.property('ADBE Effect Parade').addProperty('ADBE Gaussian Blur 2').property('ADBE Gaussian Blur 2-0001').setValue(8); } catch(ignore2) {}
            message='SUCCESS: Created a liquid-glass starter shape. This is a base treatment, not physically accurate glass refraction.';
        } else if (cmd.action === 'organize') {
            var selected=comp.selectedLayers; if (!selected || selected.length===0) throw new Error('Select one or more layers first.');
            var prefix = String(cmd.prefix || 'AI — ');
            for(var i=0;i<selected.length;i++){if(selected[i].name.indexOf(prefix)!==0)selected[i].name=prefix+selected[i].name;}
            message='SUCCESS: Renamed '+selected.length+' selected layer(s) with prefix “'+prefix+'”.';
        } else { throw new Error('Unsupported action: '+cmd.action); }
        app.endUndoGroup(); return JSON.stringify({message:message});
    } catch (e2) { try{app.endUndoGroup();}catch(ignore3){} return JSON.stringify({message:'ERROR: '+e2.toString()}); }
};

/* Return the selected still-image footage path to the local bridge. */
Vasto.getSelectedImageInfo = function () {
    try {
        if (!app.project || !(app.project.activeItem instanceof CompItem)) throw new Error('Open a composition and select a still image layer first.');
        var comp = app.project.activeItem;
        if (!comp.selectedLayers || comp.selectedLayers.length !== 1) throw new Error('Select exactly one still image layer.');
        var layer = comp.selectedLayers[0];
        if (!(layer instanceof AVLayer) || !layer.source || !layer.source.mainSource || !layer.source.mainSource.file) throw new Error('Selected layer must be a saved, local still image—not text, a shape, video, or a generated solid.');
        var file = layer.source.mainSource.file;
        var ext = file.name.toLowerCase().split('.').pop();
        if (!({png:1,jpg:1,jpeg:1,webp:1,tif:1,tiff:1,bmp:1}[ext])) throw new Error('Select a still image (PNG, JPG, WEBP, TIFF, or BMP). Video is not supported yet.');
        if (!file.exists) throw new Error('The source image file is missing or offline.');
        return JSON.stringify({path:file.fsName, name:layer.name});
    } catch (e) { return JSON.stringify({error:e.toString()}); }
};

/* Replace only if the selected layer still references the source we processed. */
Vasto.replaceSelectedImageSource = function (outputPath, expectedSourcePath) {
    var undoStarted = false;
    try {
        if (!app.project || !(app.project.activeItem instanceof CompItem)) throw new Error('The active composition changed. Transparent PNG was saved, but no layer was changed.');
        var comp = app.project.activeItem;
        if (!comp.selectedLayers || comp.selectedLayers.length !== 1) throw new Error('Selection changed. Transparent PNG was saved, but no layer was changed.');
        var layer = comp.selectedLayers[0];
        if (!(layer instanceof AVLayer) || !layer.source || !layer.source.mainSource || !layer.source.mainSource.file) throw new Error('Selected layer is no longer the original image. Transparent PNG was saved, but no layer was changed.');
        if (layer.source.mainSource.file.fsName !== expectedSourcePath) throw new Error('Selected image changed during processing. Transparent PNG was saved, but no layer was changed.');
        var outputFile = new File(outputPath);
        if (!outputFile.exists) throw new Error('Transparent PNG was not found at the output path.');
        app.beginUndoGroup('VASTOCHNIY — Remove Image Background'); undoStarted = true;
        var options = new ImportOptions(outputFile);
        var footage = app.project.importFile(options);
        layer.replaceSource(footage, false);
        app.endUndoGroup(); undoStarted = false;
        return JSON.stringify({message:'SUCCESS: Background removed. Selected layer now uses a transparent PNG; use Undo to restore the original source.'});
    } catch (e) {
        if (undoStarted) { try { app.endUndoGroup(); } catch (ignore) {} }
        return JSON.stringify({message:'ERROR: ' + e.toString()});
    }
};
