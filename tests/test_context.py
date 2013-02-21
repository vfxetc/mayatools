from common import *

import mayatools.context as ctx


class TestAttrContext(TestCase):
    
    @requires_maya
    def test_basic_transform(self):
        transform, sphere = cmds.sphere()
        attr = transform + '.translateX'
        with ctx.attrs({attr: 1}) as original:
            self.assertEqual(original.get(attr), 0)
            self.assertEqual(cmds.getAttr(attr), 1) 
        self.assertEqual(cmds.getAttr(attr), 0)
        
    @requires_maya
    def test_mutate_transform(self):
        transform, sphere = cmds.sphere()
        attr = transform + '.translateX'
        with ctx.attrs({attr: 1}) as original:
            original[attr] = 2
            self.assertEqual(cmds.getAttr(attr), 1) 
        self.assertEqual(cmds.getAttr(attr), 2)


class TestEditCommandContext(TestCase):

    @requires_maya
    def test_basic_camera(self):
        transform, cam = cmds.camera(overscan=0)
        with ctx.command(cmds.camera, cam, edit=True, overscan=1):
            self.assertEqual(cmds.camera(cam, q=True, overscan=True), 1)
        self.assertEqual(cmds.camera(cam, q=True, overscan=True), 0)
    
    @requires_maya
    def test_mutate_camera(self):
        transform, cam = cmds.camera(overscan=0)
        with ctx.command('camera', cam, edit=True, overscan=1) as original:
            self.assertEqual(cmds.camera(cam, q=True, overscan=True), 1)
            original['overscan'] = 0.5
        self.assertEqual(cmds.camera(cam, q=True, overscan=True), 0.5)


class TestCommandContext(TestCase):
    
    @requires_maya
    def test_basic_units(self):
        
        start_time = cmds.currentUnit(q=True, time=True)
        start_linear = cmds.currentUnit(q=True, linear=True)
        
        alt_time = 'ntsc' if start_time == 'film' else 'film'
        alt_linear = 'm' if start_time == 'cm' else 'cm'
        
        with ctx.command('currentUnit', time=alt_time, linear=alt_linear) as original:
            
            self.assertEqual(original.get('time'), start_time)
            self.assertEqual(cmds.currentUnit(q=True, time=True), alt_time)
            
            self.assertEqual(original.get('linear'), start_linear)
            self.assertEqual(cmds.currentUnit(q=True, linear=True), alt_linear)

        self.assertEqual(cmds.currentUnit(q=True, time=True), start_time)
        self.assertEqual(cmds.currentUnit(q=True, linear=True), start_linear)
    
    
    @requires_maya
    def test_mutate_units(self):
        
        start_time = cmds.currentUnit(q=True, time=True)
        alt_time = 'ntsc' if start_time == 'film' else 'film'
        mod_time = 'pal' if start_time == 'ntsc' else 'ntsc'
        
        self.assertNotEqual(start_time, mod_time)
        
        with ctx.command('currentUnit', time=alt_time) as original:
            self.assertEqual(original.get('time'), start_time)
            self.assertEqual(cmds.currentUnit(q=True, time=True), alt_time)
            original['time'] = mod_time

        self.assertEqual(cmds.currentUnit(q=True, time=True), mod_time)
    

class TestSelectionContext(TestCase):
    
    @requires_maya
    def test_clear(self):
    
        t, s = cmds.sphere()
        cmds.select([t, s])
        
        with ctx.selection(clear=True):
            self.assertFalse(cmds.ls(selection=True))
        
        self.assertEqual(len(cmds.ls(selection=True)), 2)
        
    @requires_maya
    def test_replace(self):
    
        t1, s1 = cmds.sphere()
        t2, s2 = cmds.sphere()
        cmds.select([t1, s1])
        
        with ctx.selection([t2, s2], replace=True):
            self.assertEqual(sorted(cmds.ls(selection=True)), sorted([t2, s2]))
            
        self.assertEqual(sorted(cmds.ls(selection=True)), sorted([t1, s1]))
    
    
class TestDeleteContext(TestCase):

    @requires_maya
    def test_pre_register(self):

        t, s = cmds.sphere()

        with ctx.delete(s):
            pass

        self.assertRaises(RuntimeError, cmds.nodeType, s)
        self.assertTrue(cmds.nodeType(t), 'transform')

    @requires_maya
    def test_post_register(self):

        with ctx.delete() as to_delete:
            t, s = cmds.sphere()
            to_delete.append(s)

        self.assertRaises(RuntimeError, cmds.nodeType, s)
        self.assertTrue(cmds.nodeType(t), 'transform')

    
    
    
    
    
    
    
    
    
    