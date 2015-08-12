import maya.cmds as cmds


cmds.file(newFile=True, force=True)


for p in cmds.getPanel( type='modelPanel' ):
    cmds.modelEditor(p, e=True, displayTextures=True)
    cmds.modelEditor(p, e=True, displayAppearance="smoothShaded")

if cmds.pluginInfo("KSNormalLookup", query=True, loaded=True):
    cmds.unloadPlugin("KSNormalLookup", f= True)

cmds.loadPlugin("KSNormalLookup")
print "loaded ", cmds.pluginInfo("KSNormalLookup", query=True, path=True)

nl_node = cmds.createNode("KSNormalLookup")

s, sph = cmds.polySphere()

locator = cmds.spaceLocator()[0]
print locator

cmds.setAttr("%s.translateX" % locator, -2)

cmds.setAttr("%s.subdivisionsAxis" % sph,  30);
cmds.setAttr("%s.subdivisionsHeight" % sph, 30);

shape_node = cmds.listRelatives(s, children = True, shapes=True)[0]
shader_node = cmds.shadingNode("surfaceShader", asShader=True)
blend_node =cmds.shadingNode("blendColors", asShader=True)

cmds.connectAttr("%s.message" % shape_node, "%s.shapeMessage" % nl_node, force=True)
cmds.connectAttr("%s.translate" % locator,  "%s.cameraLocation" % nl_node, force=True)

cmds.connectAttr("time1.outTime", "%s.time" % nl_node, force=True)

cmds.connectAttr("%s.outNormal" % nl_node,  "%s.color1" % blend_node, force=True)
for c in "RGB":
    cmds.connectAttr("%s.outFacingRatio" % nl_node, "%s.color2%s" % (blend_node, c), force=True)

cmds.connectAttr("%s.output" % blend_node,  "%s.outColor" % shader_node, force=True)

cmds.select(s)
cmds.hyperShade(assign=shader_node)
cmds.select(None)

