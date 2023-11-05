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
    "author": "Hasib345",
    "version": (0,6),
    "blender": (3, 00, 0),
    "location": "Image Editor > Texture Upscaler > ",
    "description": "Upscale Textures",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://justsomerender.gumroad.com/l/TextureUpscaler",
    "category": "Image Editor"}


import glob
import bpy
import os
import subprocess
import time


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
        prop = context.preferences.addons[__name__].preferences
        
        try:
            layout.label(text=f'Image: {im.name}')
            # layout.use_property_split = True

            layout.label(text=f'Current Resolution: {im.size[0]}X{im.size[1]}')
            layout.label(text=f'Resolution After Upscale: {im.size[0]*int(prop.scale)}X{im.size[1]*int(prop.scale)}')

            layout.prop(prop, 'replace_image' , text='Replace Texture in Material'  ,expand=True)

            layout.prop(prop, 'scale' , expand=True)
            layout.prop(prop,'models')
        except:
            layout.label(text="No Active Texture")
        layout.operator(TU_image_Upscaler.bl_idname)




class TU_image_Upscaler(bpy.types.Operator):
    """Upsacles the active imahes in image editor"""
    bl_idname = "active_image.upscale"
    bl_label = "Texture Upscaler"
    has_reports = True

    @classmethod
    def poll(cls, context):
        return context.space_data.image is not None 



    def execute(self, context):
        bpy.ops.wm.console_toggle()
        # Store the original sys.path to restore later
        start_time = time.time()
        # Get the preferences and image from the context
        prop = context.preferences.addons[__name__].preferences
        image = context.space_data.image
        # Generate the file path to save the image
        if image.file_format.lower() in image.name.lower():
            file_path = os.path.join(prop.path, image.name)
            print(file_path)
        else:
            file_path = os.path.join(prop.path, f'{image.name}.{image.file_format.lower()}')

        # Save the image to the file path
        image.save(filepath=file_path, quality=100)
        # Generate the save path for the upscaled image
        model = prop.models
        # Upscale the image
        scale = int(prop.scale)
        base, ext = os.path.splitext(image.name)
        new_path = os.path.join(prop.path, f'{base}_Upscaled{scale}x.{image.file_format.lower()}')
        addon_dir = os.path.dirname(os.path.realpath(__file__))
        exe_file = os.path.join(addon_dir, "realesrgan-ncnn-vulkan.exe")
        command = rf'{exe_file} -i "{file_path}" -o "{new_path}"  -n  {model} -s {scale}'
        try:
            subprocess.call(command)
        except Exception as ex:
            print(f'Error While Upscaling: {ex}')
            return {'CANCELLED'}
        # Load the upscaled image
        upscaled_image = bpy.data.images.load(new_path)
        # Replace the original image with the upscaled image
        if prop.replace_image:
            replace_image_nodes(image, upscaled_image)
        # Set the upscaled image as the active image in the context
        context.space_data.image = upscaled_image
        end_time = time.time()
        duration = end_time - start_time
        self.report({'INFO'}, f"Upscaled image in {duration} seconds")
        bpy.ops.wm.console_toggle()
        # print("Duration: ", duration, " seconds")
        return {'FINISHED'}

def replace_image_nodes(old_image ,Upscaled_image):
    material  = bpy.data.materials

    for mat in material:
        try:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image == old_image:
                    node.image = Upscaled_image
        except Exception as ex:
            print(f'Error While Replacing Texture in Image Nodes: {ex}')


def get_models():
    current_dir = os.path.dirname(os.path.realpath(__file__))
    models_dir = os.path.join(current_dir, 'models')

    param_files = glob.glob(os.path.join(models_dir, '*.param'))

    param_names = [os.path.splitext(os.path.basename(p))[0] for p in param_files]

    items = [(name, name, name) for name in param_names]

    return items


class TU_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    path: bpy.props.StringProperty(
        name='Path',
        description='Path to save images textures',
        default=r"C:\tmp",
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
    models:bpy.props.EnumProperty(items=get_models())


    replace_image: bpy.props.BoolProperty(
        name='Replace Image',
        description='Replace Image with Upscaled Image',
        default=True
    )
    def draw(self, context):
        layout = self.layout
        layout.label(text="Add the path where the images will be saved.")
        layout.prop(self, "path")


classes = (
    TU_image_Upscaler,
    TU_image_Panel,
    TU_Preferences,
)




def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
