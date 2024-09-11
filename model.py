import glob
import bpy
from bpy_extras.io_utils import ImportHelper
import os
import shutil
import sys



# This addon uses the ncnn model to upscale the image
# it uses ncc complied by upscaly a free image upscaler at https://github.com/upscayl/upscayl-ncnn

def get_models() -> list[tuple[str, str, str]]:
    """
    Returns a list of tuples containing the names of the models in the "models" directory.
    The tuples contain the name of the model, the name of the model, and the name of the model.
    """
    # Get the current directory of the script
    current_dir = os.path.dirname(os.path.realpath(__file__))
    # Get the directory of the models
    models_dir = os.path.join(current_dir, 'models')
    # Get a list of all the .param files in the models directory
    param_files = glob.glob(os.path.join(models_dir, '*.param'))
    # Get a list of the names of the .param files
    param_names = [os.path.splitext(os.path.basename(p))[0] for p in param_files]
    # Create a list of tuples containing the names of the models
    items = [(name, name, name) for name in param_names]

    return items


def replace_image_nodes(old_image, upscaled_image):
    """Replace the image texture in all materials with the upscaled image
    
    Args:
        old_image (bpy.types.Image): The original image to be replaced
        upscaled_image (bpy.types.Image): The upscaled image to replace the original image with
    """
    # Get all the materials in the blend file
    materials = bpy.data.materials
    
    # Loop through each material
    for material in materials:
        try:
            # Check if the material is using nodes
            if material.use_nodes:
                # Loop through each node in the material
                for node in material.node_tree.nodes:
                    # Check if the node is a texture node with the old image
                    if node.type == 'TEX_IMAGE' and node.image == old_image:
                        # Replace the image with the upscaled image
                        node.image = upscaled_image
        except Exception as error:
            # Print an error message if something goes wrong
            print(f'Error while replacing texture in image nodes: {error}')


def get_ncnn_path(addon_dir: str) -> str:
    """
    Get the path to the ncnn executable for the current platform
    
    Args:
        addon_dir (str): The directory of the addon containing the ncnn executable
    
    Returns:
        str: The path to the ncnn executable
    """
    if sys.platform.startswith('win32'):
        # Windows
        return os.path.join(addon_dir, "win-bin.exe")
    elif sys.platform.startswith('darwin'):
        # macOS
        return os.path.join(addon_dir, "mac-bin")
    elif sys.platform.startswith('linux'):
        # Linux
        return os.path.join(addon_dir, "linux-bin")
    else:
        raise Exception(f"Unsupported platform: {sys.platform}")


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

