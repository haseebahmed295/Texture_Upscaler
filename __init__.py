# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Texture Upscaler",
    "author": "haseebahmad295",
    "version": (1,2),
    "blender": (3, 00, 0),
    "location": "Image Editor > N-Panel > Texture Upscaler ",
    "description": "Upscale Textures",
    "warning": "This might Not work on older systems without Gpu",
    "wiki_url": "https://blendermarket.com/products/texture-upscaler---image-upscaler-for-blender/docs",
    "tracker_url": "https://github.com/Hasib345/Texture_Upscaler/issues",
    "category": "System"}

import threading
import bpy
import os
import subprocess
import time
from .model import*

class TU_image_Panel(bpy.types.Panel):
    """Panel to Upscale Textures"""
    bl_idname = "IMAGE_EDITOR_PT_texture_upscaler"
    bl_label = "Texture Upscaler"
    #bl_options =  {'DEFAULT_CLOSED'}

    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Texture Upscaler"
    

    def draw(self, context):
        layout = self.layout
        im = context.space_data.image
        prop = context.preferences.addons[__package__].preferences
        
        try:
            layout.label(text=f'Image: {im.name}')
            # layout.use_property_split = True

            layout.label(text=f'Current Resolution: {im.size[0]}X{im.size[1]}')
            layout.label(text=f'Resolution After Upscale: {im.size[0]*int(prop.scale)}X{im.size[1]*int(prop.scale)}')

            layout.prop(prop, 'replace_image' , text='Replace Texture in Material'  ,expand=True)

            layout.prop(prop, 'scale' , expand=True)
            layout.prop(context.scene,'models')
            lable = "Upscale" if not prop.runing else "Please Wait..."
            layout.operator(TU_image_Upscaler.bl_idname , icon='STICKY_UVS_VERT' , text=lable)
        except:
            layout.label(text="No Active Image in Image Editor" , icon = 'ERROR')
        
class TU_image_Upscaler(bpy.types.Operator):
    """Upscales the active images in image editor"""
    bl_idname = "active_image.upscale"
    bl_label = "Texture Upscaler"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return not context.preferences.addons[__package__].preferences.runing

    def execute(self, context):
        prop = context.preferences.addons[__package__].preferences
        prop.runing = True
        image = context.space_data.image
        space_data = context.space_data
        file_path = os.path.join(prop.path, f'{image.name}.{image.file_format.lower()}')
        image.save(filepath=file_path, quality=100)
        model = context.scene.models
        scale = int(prop.scale)
        base, ext = os.path.splitext(image.name)
        new_path = os.path.join(prop.path, f'{base}_upscaled_{scale}x.{image.file_format.lower()}')
        addon_dir = os.path.dirname(os.path.realpath(__file__))
        ncnn_file = get_ncnn_path(addon_dir)

        def callback(new_path ,image , space_data):
            upscaled_image = bpy.data.images.load(new_path)
            prop = context.preferences.addons[__package__].preferences
            if prop.replace_image:
                replace_image_nodes(image, upscaled_image)
            space_data.image = upscaled_image
            prop.runing = False
        im_thread = threading.Thread(target=self.run_model, args=(space_data ,image , prop ,file_path , new_path , model , scale , ncnn_file , callback, ))
        im_thread.start()
        return {'FINISHED'}

    def run_model(self, space_data, image, prop, file_path, new_path, model, scale, ncnn_file, callback):
        # Construct the command as a list
        command = [
            ncnn_file,
            "-i",
            file_path,
            "-o",
            new_path,
            "-n",
            model,
            "-s",
            str(scale)
        ]
        
        # Add GPU option if specified
        if prop.gpu != "Auto":
            command.extend(["-g", str(prop.gpu)])
        
        try:
            # Execute the command using subprocess.call with the constructed list
            p = subprocess.call(command)
            if p == 4294967295:
                prop.runing = False
                self.report({'ERROR'}, "Your System does not support Vulkan")
                return {'CANCELLED'}
        except Exception as e:
            prop.runing = False
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        callback(new_path, image, space_data)

class TU_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    path: bpy.props.StringProperty(
        name='Path to save upscaled images',
        description='Set the path where you want to save images textures \n Make sure path has permission to write',
        default='C:/temp',
        subtype='DIR_PATH'
    )
    scale:bpy.props.EnumProperty(items = [
        ('2', '2x', '2'),
        ('3', '3x', '3'),
        ('4', '4x', '4'),
        ],
    name= 'Select Scale Level:',
    description = "Scale Level for Upscaling",
    default='4'
    )
    replace_image: bpy.props.BoolProperty(
        name='Replace Image',
        description='Replace Image with Upscaled Image',
        default=False
    )
    runing: bpy.props.BoolProperty(
        default=False
    )
    gpu:bpy.props.EnumProperty(items = [
        ('Auto', 'Auto', 'Auto'),
        ('0', 'Device 0', '0'),
        ('1', 'Device 1', '1'),
        ('2', 'Device 2', '2'),
        ],
    name= 'Select Gpu device',
    description = "Gpu device to use For Upscaling \n Leave Auto if you are not sure \n Device 0 is mostly Cpu and Device 1 and Device 2 is mostly Gpu",
    default='Auto'
    )
    def draw(self, context):
        layout = self.layout
        layout.label(text="Add the path where the images will be saved.")
        layout.prop(self, "path")
        layout.prop(self, "gpu")
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Option to add your custom ncnn Model" , icon = 'INFO')
        col.operator("texture_upscaler.import_model" , text="Add Model", icon = 'FILE_FOLDER')


classes = (
    TU_image_Upscaler,
    TU_image_Panel,
    model_importer,
    TU_Preferences,
    
)


def register():
    bpy.types.Scene.models = bpy.props.EnumProperty(items=get_models())
    for cls in classes:
        bpy.utils.register_class(cls)
    

def unregister():
    del bpy.types.Scene.models
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __package__ == "__main__":
    register()
