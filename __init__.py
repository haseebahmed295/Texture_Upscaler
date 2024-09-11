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
        image = context.space_data.image
        prop = context.preferences.addons[__package__].preferences
        
        if image:
            info_header , info_panel = layout.panel_prop(context.scene , "TU_info")
            info_header.label(text = "Image Info")
            if info_panel:
                col = info_panel.column(align=True)
                box = col.box()
                box.label(text=f'Image: {image.name}')
                # layout.use_property_split = True
                box = col.box()
                box.label(text=f'Current Res: {image.size[0]}X{image.size[1]}')
                box = col.box()
                
                if prop.use_custom_width:
                    text=f'Upscale Res: {prop.custom_width}X{int((prop.custom_width/image.size[0])*image.size[1])}'
                else:
                    text=f'Upscale Res: {image.size[0]*int(prop.scale)}X{image.size[1]*int(prop.scale)}'
                box.label(text = text)

            row = layout.row(align=True)
            row.prop(prop, 'replace_image' , text='Replace in Materials'  ,expand=True)
            row.prop(prop , "use_compress" , icon="OBJECT_DATAMODE" , text="")
            row.prop(prop , "use_custom_width" , icon="MOD_LENGTH" , text="")

            row = layout.row(align=True)
            row.label(text= "Image Scale:")
            row.prop(prop, 'scale' ,text= "")
            
            if prop.use_custom_width:
                row.active = False
                c_row = layout.row(align=True)
                c_row.label(text="Custom Width: ")
                c_row.prop(prop , "custom_width" , text="")

            if prop.use_compress:
                c_row = layout.row(align=True)
                c_row.label(text="Compression: ")
                c_row.prop(prop , "compress" , text="")
                
            layout.prop(context.scene,'models')
            lable = "Upscale" if not prop.runing else "Please Wait..."
            layout.operator(TU_image_Upscaler.bl_idname , icon='STICKY_UVS_VERT' , text=lable)
        else:
            layout.label(text="No Active Image in Image Editor" , icon = 'ERROR')
        
class TU_image_Upscaler(bpy.types.Operator):
    """Upscales the active images in image editor"""
    bl_idname = "active_image.upscale"
    bl_label = "Texture Upscaler"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return not context.preferences.addons[__package__].preferences.runing
    def modal(self, context, event: bpy.types.Event) -> set:
        """
        Handles the timer events for the modal operator.

        This function is called every 0.01s while the operator is running.
        It checks if the upscaling thread is outputing any things and if so, it reports the output and resets the
        is_updated flag so that the operator can be exited.
        """
        prop = context.preferences.addons[__package__].preferences

        if event.type == 'TIMER':
            # Check if the upscaling thread is done
            if self._is_updated:
                # The upscaling thread is done, report the result
                self.report({"INFO"} , f"Progress: {self._callback_rep}")
                # Reset the is_updated flag
                self._is_updated = False
                # Return the PASS_THROUGH to continue running the operator
                return {'PASS_THROUGH'}

            # Check if the upscaling thread is still running
            if not prop.runing:
                # The upscaling thread is not running, report the result
                if self._is_error:
                    self.report({"INFO"} , "Upscaling Failed ")
                else:
                    self.report({"INFO"} , "Upscaling Done ")
                # Return FINISHED to exit the operator
                return {'FINISHED'}

        # Return PASS_THROUGH to continue running the operator
        return {'PASS_THROUGH'}
    def execute(self, context):
        """
        Runs the image upscaling process when the operator is called
        """
        # Get the preferences from the addon
        prop = context.preferences.addons[__package__].preferences
        prop.runing = True
        # Get the active image in the image editor
        image = context.space_data.image
        space_data = context.space_data
        # Save the image to a file
        file_path = os.path.join(prop.path, f'{image.name}.{image.file_format.lower()}')
        image.save(filepath=file_path, quality=100)
        # Get the model to use for upscaling
        model = context.scene.models
        scale = prop.scale
        # Get the output file name and path
        base, ext = os.path.splitext(image.name)
        if prop.out_format != "Auto":
            form = prop.out_format
        else:
            form = image.file_format.lower()
        new_path = os.path.join(prop.path, f'{base}_{scale}x.{form}')

        # Get the path to the ncnn executable
        addon_dir = os.path.dirname(os.path.realpath(__file__))
        ncnn_file = get_ncnn_path(addon_dir)

        # Define a callback function to run after the upscaling is done
        def callback(new_path,image):
            """
            This function will be run after the upscaling is done
            """
            try:
                upscaled_image = bpy.data.images.load(new_path)
            except Exception as e:
                self._is_error = True
                self._callback_report = f"Error: {e}"
                return
            if prop.replace_image:
                replace_image_nodes(image, upscaled_image)
            space_data.image = upscaled_image
            prop.runing = False

        self._callback_report = None
        self._is_updated = False
        self._is_error = False
        # Start the upscaling thread
        upscaling_thread = threading.Thread(
            target=self.run_model,
            args=(
                image, prop, file_path, new_path, model, scale, ncnn_file, callback
            )
        )
        upscaling_thread.start()
        
        # Start the timer to check for updates
        self.report({"INFO"} , "Upscaling... 😎")
        self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def run_model(self, image, prop, file_path, new_path, model, scale, ncnn_file, callback):
        """
        Runs the upscaling model using the provided parameters
        """
        # Construct the command as a list
        command = [
            ncnn_file,
            "-i",
            file_path,
            "-o",
            new_path,
            "-n",
            model,
        ]
        if prop.use_custom_width:
            command.extend(["-w", str(prop.custom_width)])
        else:
            command.extend(["-s", str(scale)])

        if prop.use_compress:
            command.extend(["-c", str(prop.compress)])
        # Add GPU option if specified
        if prop.gpu != "Auto":
            command.extend(["-g", str(prop.gpu)])
        # Add format option if specified
        if prop.out_format != "Auto":
            command.extend(["-f", prop.out_format])
        
        try:
            # Execute the command using subprocess.call with the constructed list
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

            for line in iter(process.stdout.readline, ""):
                print(line.strip())
                if "%" in line.strip():
                    # Set the callback report to the progress of the upscaling
                    self._callback_rep = line.strip()
                    self._is_updated = True
                elif " Error:" in line.strip():
                    # Set the callback report to the error message
                    prop.runing = False
                    self._is_error = True
                    self.report({'ERROR'}, f"{line.strip()}")
                    return {'CANCELLED'}
        except Exception as e:
            # Set the callback report to the error message
            prop.runing = False
            self.is_error = True
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        # Call the callback function with the new path and the image
        callback(new_path, image)

class TU_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    path: bpy.props.StringProperty(
        name='Save Folder',
        description='Set the folder where you want to save images textures \n Make sure folder has permission to write',
        default='C:/temp',
        subtype='DIR_PATH'
    )
    scale:bpy.props.IntProperty(
        name = "Image Scale",
        description="Number of Times the image get Scaled",
        default=4,
        min=1,
        max=16,
        subtype='FACTOR',
    )
    replace_image: bpy.props.BoolProperty(
        name='Replace Image',
        description='Replace texture in materials with upscaled texture',
        default=False
    )
    runing: bpy.props.BoolProperty(
        default=False
    )
    use_custom_width:bpy.props.BoolProperty(
        name = "Use Custom Width",
        description = "Upscale image to custom width intead of xScale",
        default=False
    )
    custom_width:bpy.props.IntProperty(
        name = "Custom Width",
        description="Width of Upscaled Images in px",
        default=1920,
        min=200, max= 10000,
        subtype="PIXEL"
        )
    use_compress:bpy.props.BoolProperty(
        name = "Use Compression",
        description="Compress the Upscaled image to reduce size",
        default=False
    )
    compress:bpy.props.IntProperty(
        name = "Amount of Compression in %",
        default=0,
        min=0, max= 100,
        subtype="PERCENTAGE"
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
    out_format:bpy.props.EnumProperty(items = [
        ('Auto', 'Auto', 'Auto'),
        ('png', 'png', 'png'),
        ('jpg', 'jpg', 'jpg'),
        ('webp', 'webp', 'webp'),
        ],
    name= 'Select Output Format',
    description = "Output Format of Upscaled Images . Leave it at auto if you want to upscaled image to have same format as orignal",
    default='Auto'
    )
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Add the path where the images will be saved.")
        layout.prop(self, "path")
        layout.prop(self, "gpu")
        layout.prop(self, "out_format")
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
    setattr(bpy.types.Scene , "TU_info" , bpy.props.BoolProperty(default=True))
    for cls in classes:
        bpy.utils.register_class(cls)
    

def unregister():
    del bpy.types.Scene.models
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __package__ == "__main__":
    register()
