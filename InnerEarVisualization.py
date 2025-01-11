import vtk
import os

def LoadFiles(nrrdFolder: str, vtkFolder: str) -> tuple[list[vtk.vtkActor], vtk.vtkNrrdReader | None]:
    """
    Loads multiple NRRD files and VTK models
    """
    vtkActors = []
    reader = None

    for filename in os.listdir(nrrdFolder):
        if filename.endswith(".nrrd"):
            nrrdPath = os.path.join(nrrdFolder, filename)
            
            reader = vtk.vtkNrrdReader()
            reader.SetFileName(nrrdPath)
            reader.Update()

            #TODO Flip the image along the Y-axis
            flippedReader = vtk.vtkImageFlip()
            flippedReader.SetInputConnection(reader.GetOutputPort())
            flippedReader.SetFilteredAxis(1)  # 0 for X, 1 for Y, 2 for Z
            flippedReader.Update()

            # Create planes for the chosen NRRD file
            planeActors = CreatePlanes(flippedReader)
            vtkActors.extend(planeActors)
            break  # Load only first NRRD file

    # Load the colored parts of the inner ear
    earActors = ColorSpecificParts(vtkFolder)
    vtkActors.extend(earActors)

    return vtkActors, reader

def ColorSpecificParts(vtkFolder: str) -> list[vtk.vtkActor]:
    """
    Changes each part of the inner ear to a specific color using VTK files
    """
    actors = []
    colors = [
        (0.6, 1.0, 0.6),      # Light Green
        (0.0, 1.0, 0.0),      # Green
        (0.0, 0.0, 1.0),      # Blue
        (0.5, 0.5, 0.5),      # Gray
        (0.6, 0.8, 1.0),      # Light Blue
        (1.0, 0.7, 0.7),      # Pink
        (1.0, 0.0, 0.0),      # Red
        (0.6, 0.4, 0.2)       # Brownish
    ]

    for i, filename in enumerate(os.listdir(vtkFolder)):
        if filename.endswith(".vtk"):
            filepath = os.path.join(vtkFolder, filename)
            
            reader = vtk.vtkPolyDataReader()
            reader.SetFileName(filepath)
            reader.Update()

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(reader.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            
            # Set a specific color for each part
            color = colors[i % len(colors)]
            actor.GetProperty().SetColor(color)
            
            # Set opacity as 0.1 for the temporal bone, internal jugular vein and internal carotid vein
            #to improve visibilty of the inner ear
            if(filename == "Model_3_Temporal_Bone.vtk" or filename == "Model_21_Internal_Jugular_Vein.vtk" or filename == "Model_24_Internal_Carotid_Artery.vtk"):
                actor.GetProperty().SetOpacity(0.1) 

            actors.append(actor)

    return actors

def CreatePlanes(reader: vtk.vtkNrrdReader) -> list[vtk.vtkImageActor]:
    """
    Create three planes (sagittal, axial, coronal) for the NRRD file
    """

    data = reader.GetOutput()
    dimensions = data.GetDimensions()  # Return the dimensions of the data
    spacing = data.GetSpacing()        # Set the spacing between the data points in the X, Y, and Z directions
    origin = data.GetOrigin()          # Set the beginning point of the data

    # Calculate the center of the volume
    center = [
        origin[i] + (dimensions[i] - 1) * spacing[i] / 2.0
        for i in range(3)
    ]

    # Create the sagittal plane
    sagittal = vtk.vtkImageActor()
    sagittal.GetMapper().SetInputConnection(reader.GetOutputPort())
    sagittal.SetDisplayExtent(
        int(center[0] / spacing[0]),  # Index of the center in the X axis
        int(center[0] / spacing[0]),
        0,
        dimensions[1] - 1,           # Full range in the Y axis
        0,
        dimensions[2] - 1            # Full range in the Z axis
    )

    # Create the axial plane
    axial = vtk.vtkImageActor()
    axial.GetMapper().SetInputConnection(reader.GetOutputPort())
    axial.SetDisplayExtent(
        0,
        dimensions[0] - 1,           # Full range in the X axis
        0,
        dimensions[1] - 1,           # Full range in the Y axis
        int(center[2] / spacing[2]), # Index of the center in the Z axis
        int(center[2] / spacing[2])
    )

    # Create the coronal plane
    coronal = vtk.vtkImageActor()
    coronal.GetMapper().SetInputConnection(reader.GetOutputPort())
    coronal.SetDisplayExtent(
        0,
        dimensions[0] - 1,           # Full range in the X axis
        int(center[1] / spacing[1]), # Index of the center in the Y axis
        int(center[1] / spacing[1]),
        0,
        dimensions[2] - 1            # Full range in the Z axis
    )

    # Set the color window, color level for each plane
    for plane in [sagittal, axial, coronal]:
        plane.GetProperty().SetColorWindow(2000)  
        plane.GetProperty().SetColorLevel(1000)    

    return [sagittal, axial, coronal]



def Render3D(objects: list[vtk.vtkActor]) -> None:
    """
    Renders the 3D visualization
    """
    # Set background color
    colors = vtk.vtkNamedColors()
    colors.SetColor("BkgColor", [26, 51, 102, 255])
    # Create renderer
    renderer = vtk.vtkRenderer()
    
    # Add all actors
    for obj in objects:
        renderer.AddActor(obj)

    # Create render window
    renderWindow = vtk.vtkRenderWindow()
    renderWindow.AddRenderer(renderer)
    renderWindow.SetSize(800, 800)

    # Create interactor
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renderWindow)

    # Set background and camera
    renderer.SetBackground(colors.GetColor3d("BkgColor"))
    renderer.ResetCamera()

    # Render and start interaction
    renderWindow.Render()
    interactor.Start()

def main():
    nrrdFolder = "inner-ear-2018-02/image-volumes"
    vtkFolder = "inner-ear-2018-02/models"

    # Load actors from NRRD and VTK files
    actors, reader = LoadFiles(nrrdFolder, vtkFolder)

    # Render all actors
    Render3D(actors)

if __name__ == "__main__":
    main()