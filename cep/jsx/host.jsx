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
            var doc = textProp.value; doc.fontSize = Math.min(140, Math.max(48, 1080 / Math.max(5, String(cmd.text || '').length) * 0.65)); doc.applyFill = true; doc.fillColor = [1,1,1]; doc.justification = ParagraphJustification.CENTER_JUSTIFY; textProp.setValue(doc);
            layer.property('ADBE Transform Group').property('ADBE Position').setValue([comp.width/2, comp.height/2]);
            var scale = layer.property('ADBE Transform Group').property('ADBE Scale');
            var dur = Math.max(0.2, Math.min(5, Number(cmd.duration) || 0.8));
            scale.setValueAtTime(0,[0,0]); scale.setValueAtTime(dur*0.72,[112,112]); scale.setValueAtTime(dur,[100,100]);
            try { scale.setInterpolationTypeAtKey(1,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER); scale.setInterpolationTypeAtKey(2,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER); scale.setInterpolationTypeAtKey(3,KeyframeInterpolationType.BEZIER,KeyframeInterpolationType.BEZIER); } catch(ignore) {}
            layer.property('ADBE Transform Group').property('ADBE Opacity').setValueAtTime(0,0); layer.property('ADBE Transform Group').property('ADBE Opacity').setValueAtTime(Math.min(0.25,dur/2),100);
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
