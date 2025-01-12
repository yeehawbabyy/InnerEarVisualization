import vtk
import os

class SliderCallback:
    
    def __init__(self, plane, axis):
        self.plane = plane
        self.axis = axis

    def __call__(self, obj, event):
        position = int(obj.GetRepresentation().GetValue())
        extent = list(self.plane.GetDisplayExtent())
        extent[self.axis * 2] = position
        extent[self.axis * 2 + 1] = position
        self.plane.SetDisplayExtent(*extent)

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

            break  # Load only the first NRRD file
    
    # Load the outline
    outlineActor = CreateOutline(reader)
    vtkActors.append(outlineActor)

    # Load the colored parts of the inner ear
    earActors = ColorSpecificParts(vtkFolder)
    vtkActors.extend(earActors)

    return vtkActors, reader

def CreateOutline(reader: vtk.vtkNrrdReader) -> vtk.vtkActor:
    """
    Creates an outline around the NRRD file
    """
    outlineData = vtk.vtkOutlineFilter()
    outlineData.SetInputConnection(reader.GetOutputPort())

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(outlineData.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(255, 255, 255)

    return actor

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
    colorNames = [
        "Light Green",
        "Green",
        "Blue",
        "Gray",
        "Light Blue",
        "Pink",
        "Red",
        "Brownish"
    ]

    for i, filename in enumerate(os.listdir(vtkFolder)):
        if filename.endswith(".vtk"):
            filepath = os.path.join(vtkFolder, filename)

            structureName = filename.split('_', 2)[-1].replace('.vtk', '')
            structureName = structureName.replace('_', ' ')

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

            print(f"Structure: {structureName}")
            print(f"Color: {colorNames[i % len(colorNames)]}")
            print("-" * 40)

            # Set opacity as 0.1 for specific models to improve visibility
            if filename in ["Model_3_Temporal_Bone.vtk", "Model_21_Internal_Jugular_Vein.vtk", "Model_24_Internal_Carotid_Artery.vtk"]:
                actor.GetProperty().SetOpacity(0.1)
                print(f"Note: {structureName} has reduced opacity (0.1)")
                print("-" * 40)

            actors.append(actor)

    return actors

def CreatePlanes(reader: vtk.vtkNrrdReader) -> list[vtk.vtkImageActor]:
    """
    Create three planes (sagittal, axial, coronal) for the NRRD file
    """
    data = reader.GetOutput()
    dimensions = data.GetDimensions()
    spacing = data.GetSpacing()
    origin = data.GetOrigin()

    # Calculate the center of the volume
    center = [
        origin[i] + (dimensions[i] - 1) * spacing[i] / 2.0
        for i in range(3)
    ]

    # Create separate flip filters for each plane
    flipX = vtk.vtkImageFlip()
    flipX.SetInputConnection(reader.GetOutputPort())
    flipX.SetFilteredAxis(0)  # Flip along X-axis
    flipX.Update()

    flipY = vtk.vtkImageFlip()
    flipY.SetInputConnection(reader.GetOutputPort())
    flipY.SetFilteredAxis(1)  # Flip along Y-axis
    flipY.Update()

    # Chain flip for axial plane - flip Y after X
    flipXY = vtk.vtkImageFlip()
    flipXY.SetInputConnection(flipX.GetOutputPort())
    flipXY.SetFilteredAxis(1)  # Flip along Y-axis
    flipXY.Update()

    # Chain flip for coronal plane - flip Y and then X
    flipYX = vtk.vtkImageFlip()
    flipYX.SetInputConnection(flipY.GetOutputPort())
    flipYX.SetFilteredAxis(0)  # Flip along X-axis
    flipYX.Update()

    # Chain flip for the sagittal plane - flip X and then Y
    sagittal = vtk.vtkImageActor()
    sagittal.GetMapper().SetInputConnection(flipXY.GetOutputPort())
    sagittal.SetDisplayExtent(
        int(center[0] / spacing[0]),
        int(center[0] / spacing[0]),
        0,
        dimensions[1] - 1,
        0,
        dimensions[2] - 1
    )

    # Create the axial plane using combined X and Y axis flips
    axial = vtk.vtkImageActor()
    axial.GetMapper().SetInputConnection(flipXY.GetOutputPort())
    axial.SetDisplayExtent(
        0,
        dimensions[0] - 1,
        0,
        dimensions[1] - 1,
        int(center[2] / spacing[2]),
        int(center[2] / spacing[2])
    )

    # Create the coronal plane using combined Y and X axis flips
    coronal = vtk.vtkImageActor()
    coronal.GetMapper().SetInputConnection(flipYX.GetOutputPort())
    coronal.SetDisplayExtent(
        0,
        dimensions[0] - 1,
        int(center[1] / spacing[1]),
        int(center[1] / spacing[1]),
        0,
        dimensions[2] - 1
    )

    # Set the color window, color level for each plane
    for plane in [sagittal, axial, coronal]:
        plane.GetProperty().SetColorWindow(2000)
        plane.GetProperty().SetColorLevel(1000)

    return [sagittal, axial, coronal]

def AddSliders(renderer, interactor, planes):
    """
    Adds 3D sliders to control the positions of the planes (sagittal, axial, coronal)
    """
    axis_labels = ["Sagittal", "Axial", "Coronal"]
    sliders = []

    sliderLength = 75
    # Pozycje początkowe i końcowe dla każdego suwaka w przestrzeni 3D
    positions = [
        [[-75, -75, 100], [-75+sliderLength, -75, 100]],  # Sagittal slider (poziomy, na lewo)
        [[-75, -75, 100+sliderLength], [-75, -75, 101.25]],      # Axial slider (pionowy, po prawej)
        [[-75, -75+sliderLength, 100], [-75, -75, 100]]      # Coronal slider (pionowy, z tyłu)
    ]

    for i, (plane, axis) in enumerate(zip(planes, [0, 2, 1])):  # Mapowanie: sagittal -> X, axial -> Z, coronal -> Y
        sliderRep = vtk.vtkSliderRepresentation3D()
        sliderRep.SetMinimumValue(0)
        sliderRep.SetMaximumValue(plane.GetInput().GetDimensions()[axis] - 1)
        sliderRep.SetValue(plane.GetDisplayExtent()[axis * 2])
        sliderRep.GetSliderProperty().SetColor(1, 0, 0)  # knob color - red
        sliderRep.GetSelectedProperty().SetColor(1, 1, 1)  # slider color - white
    
        # Ustaw pozycję suwaka w przestrzeni 3D
        sliderRep.SetPoint1InWorldCoordinates(*positions[i][0])
        sliderRep.SetPoint2InWorldCoordinates(*positions[i][1])

        # Tworzenie suwaka i przypisanie callbacku
        slider = vtk.vtkSliderWidget()
        slider.SetInteractor(interactor)
        slider.SetRepresentation(sliderRep)
        slider.AddObserver("InteractionEvent", SliderCallback(plane, axis))

        sliders.append(slider)

    return sliders


def Render3DWithSliders(objects: list[vtk.vtkActor], planes: list[vtk.vtkImageActor]) -> None:
    """
    Renders the 3D visualization with 3D sliders to control the planes.
    """
    # Set background color
    colors = vtk.vtkNamedColors()
    colors.SetColor("BkgColor", [0, 0, 0, 255])

    # Create renderer
    renderer = vtk.vtkRenderer()

    # Add all static actors (models, etc.)
    for obj in objects:
        renderer.AddActor(obj)

    # Add only the first instance of each plane
    for plane in planes:
        renderer.AddActor(plane)

    # Create render window
    renderWindow = vtk.vtkRenderWindow()
    renderWindow.AddRenderer(renderer)
    renderWindow.SetSize(800, 800)

    # Create interactor
    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renderWindow)

    # Set interaction style
    style = vtk.vtkInteractorStyleTrackballCamera()
    interactor.SetInteractorStyle(style)

    # Set background and camera
    renderer.SetBackground(colors.GetColor3d("BkgColor"))
    renderer.ResetCamera()

    # Add sliders for planes
    sliders = AddSliders(renderer, interactor, planes)

    # Initialize and start interaction
    renderWindow.Render()
    for slider in sliders:
        slider.EnabledOn()
    interactor.Initialize()
    interactor.Start()

def main():
    nrrdFolder = "inner-ear-2018-02/image-volumes"
    vtkFolder = "inner-ear-2018-02/models"

    # Load actors from NRRD and VTK files
    actors, reader = LoadFiles(nrrdFolder, vtkFolder)

    # Create planes
    planes = CreatePlanes(reader)

    # Render all actors with sliders
    Render3DWithSliders(actors, planes)

if __name__ == "__main__":
    main()