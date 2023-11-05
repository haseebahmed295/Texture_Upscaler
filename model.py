import glob
import bpy
from bpy_extras.io_utils import ImportHelper
import os
import shutil

def get_models():

    current_dir = os.path.dirname(os.path.realpath(__file__))
    models_dir = os.path.join(current_dir, 'models')

    param_files = glob.glob(os.path.join(models_dir, '*.param'))

    param_names = [os.path.splitext(os.path.basename(p))[0] for p in param_files]

    items = [(name, name, name) for name in param_names]

    return items

class model_importer(bpy.types.Operator ,ImportHelper):
    bl_idname = "texture_upscaler.import_model"
    bl_label = "Add Model"
    bl_description = 'You can add your custom ncnn Model using this operator from the File Browser. \n Note: Only .param and .bin files are supported.'

    filename_ext = ".param"

    filter_glob: bpy.props.StringProperty(
        default="*.param;*.bin",
        options={'HIDDEN'},
        maxlen=1024,
    )

    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement)
    
    def execute(self, context):
    # Get the directory of the selected files
        directory = os.path.dirname(self.filepath)
        
        # If no files are selected, get all .param and .bin files
        if not self.files:
            files = [f for f in os.listdir(directory) if f.endswith('.param') or f.endswith('.bin')]
        else:
            # If only one file is selected, search for the other file of the same name
            if len(self.files) == 1:
                basename = os.path.splitext(self.files[0].name)[0]
                files = [f for f in os.listdir(directory) if f.startswith(basename) and (f.endswith('.param') or f.endswith('.bin'))]
            else:
                # If multiple files are selected, get only those files
                files = [f.name for f in self.files]
        
        # Define the destination directory
        addon_directory = os.path.dirname(os.path.realpath(__file__))
        model_directory = os.path.join(addon_directory, "models")
        
        # Create the model directory if it doesn't exist
        if not os.path.exists(model_directory):
            os.makedirs(model_directory)
        
        # Copy each file to the model directory in the addon folder
        for file in files:
            source = os.path.join(directory, file)
            destination = os.path.join(model_directory, file)
            shutil.copy2(source, destination)
            print(f"Added to models : {file} ")

        bpy.types.Scene.models = bpy.props.EnumProperty(items=get_models())
        return {'FINISHED'}

