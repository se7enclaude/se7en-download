/*
 * se7en — "Send to Upscaler" for Adobe After Effects (ExtendScript).
 *
 * Install:  copy this file to
 *   C:\Program Files\Adobe\Adobe After Effects <version>\Support Files\Scripts\ScriptUI Panels\
 * then enable  Edit › Preferences › Scripting & Expressions › "Allow Scripts to Write Files and Access Network".
 * Open it from  Window › se7en_SendToUpscaler.jsx  (dockable panel) or  File › Scripts.
 *
 * Usage: select footage items in the Project panel, pick a model/scale, click "Send to Upscaler".
 * se7en must be running. The script calls `se7en-cli.exe upscale --wait`, which blocks
 * until the render finishes, then imports the result next to the original footage.
 */
(function (thisObj) {
  var CLI_CANDIDATES = [
    Folder.userData.parent.fsName + "\\Local\\Programs\\se7en\\se7en-cli.exe",
    "C:\\Program Files\\se7en\\se7en-cli.exe"
  ];

  function findCli() {
    for (var i = 0; i < CLI_CANDIDATES.length; i++) {
      if (new File(CLI_CANDIDATES[i]).exists) return CLI_CANDIDATES[i];
    }
    var f = File.openDialog("Locate se7en-cli.exe", "*.exe");
    return f ? f.fsName : null;
  }

  function q(s) { return '"' + s.replace(/"/g, '\\"') + '"'; }

  function buildUI(obj) {
    var win = obj instanceof Panel ? obj : new Window("palette", "se7en", undefined, { resizeable: true });
    win.orientation = "column";
    win.alignChildren = ["fill", "top"];
    var g1 = win.add("group");
    g1.add("statictext", undefined, "Model:");
    var model = g1.add("dropdownlist", undefined, ["realesrgan-x4plus", "realesr-animevideov3", "realesrgan-x4plus-anime", "classic-lanczos"]);
    model.selection = 0;
    var g2 = win.add("group");
    g2.add("statictext", undefined, "Scale:");
    var scale = g2.add("dropdownlist", undefined, ["2", "4"]);
    scale.selection = 0;
    var reimport = win.add("checkbox", undefined, "Import result into the project");
    reimport.value = true;
    var btn = win.add("button", undefined, "Send to Upscaler");
    var status = win.add("statictext", undefined, "Select footage in the Project panel.", { multiline: true });
    status.preferredSize = [260, 40];

    btn.onClick = function () {
      var items = app.project.selection;
      var sources = [];
      for (var i = 0; i < items.length; i++) {
        if (items[i] instanceof FootageItem && items[i].file) sources.push(items[i]);
      }
      if (!sources.length) { alert("Select at least one footage item with a file on disk."); return; }
      var cli = findCli();
      if (!cli) return;
      app.beginUndoGroup("se7en upscale");
      for (var k = 0; k < sources.length; k++) {
        status.text = "Upscaling " + sources[k].name + " (" + (k + 1) + "/" + sources.length + ")…";
        win.layout.layout(true);
        var cmd = q(cli) + " upscale " + q(sources[k].file.fsName) + " --model " + model.selection.text +
          " --scale " + scale.selection.text + " --wait";
        var out = system.callSystem("cmd /c " + q(cmd + " 2>nul"));
        var lines = out.replace(/\r/g, "").split("\n");
        var result = "";
        for (var l = lines.length - 1; l >= 0; l--) { if (lines[l].length > 3) { result = lines[l]; break; } }
        if (!result || !new File(result).exists) {
          status.text = "Failed: " + (out || "no output (is se7en running?)");
          continue;
        }
        if (reimport.value) {
          var imported = app.project.importFile(new ImportOptions(new File(result)));
          if (sources[k].parentFolder) imported.parentFolder = sources[k].parentFolder;
        }
        status.text = "Done: " + result;
      }
      app.endUndoGroup();
    };
    if (win instanceof Window) { win.center(); win.show(); } else { win.layout.layout(true); }
    return win;
  }

  buildUI(thisObj);
})(this);
