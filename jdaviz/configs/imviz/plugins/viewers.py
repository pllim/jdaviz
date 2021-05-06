import numpy as np

from astropy.wcs.wcsapi import BaseHighLevelWCS

from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry

__all__ = ['ImvizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(BqplotImageView):

    tools = ['bqplot:panzoom', 'bqplot:contrastbias', 'bqplot:rectangle', 'bqplot:circle',
             'bqplot:matchwcs']

    default_class = None

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.label_mouseover = None

        self.add_event_callback(self.on_mouse_or_key_event, events=['mousemove', 'mouseenter',
                                                                    'mouseleave', 'keydown'])

        self.state.show_axes = False

    def on_mouse_or_key_event(self, data):

        # Find visible layers
        visible_layers = [layer for layer in self.state.layers if layer.visible]

        if len(visible_layers) == 0:
            return

        if self.label_mouseover is None:
            if 'g-coords-info' in self.session.application._tools:
                self.label_mouseover = self.session.application._tools['g-coords-info']
            else:
                return

        if data['event'] == 'mousemove':

            # Display the current cursor coordinates (both pixel and world) as
            # well as data values. For now we use the first dataset in the
            # viewer for the data values.

            # Extract first dataset from visible layers and use this for coordinates - the choice
            # of dataset shouldn't matter if the datasets are linked correctly
            image = visible_layers[0].layer

            # Extract data coordinates - these are pixels in the image
            x = data['domain']['x']
            y = data['domain']['y']

            maxsize = int(np.ceil(np.log10(np.max(image.shape)))) + 3

            fmt = 'x={0:0' + str(maxsize) + '.1f} y={1:0' + str(maxsize) + '.1f}'

            self.label_mouseover.pixel = (fmt.format(x, y))

            if isinstance(image.coords, BaseHighLevelWCS):
                # Convert these to a SkyCoord via WCS - note that for other datasets
                # we aren't actually guaranteed to get a SkyCoord out, just for images
                # with valid celestial WCS
                try:
                    celestial_coordinates = (image.coords.pixel_to_world(x, y).icrs
                                             .to_string('hmsdms', precision=4, pad=True))
                except Exception:
                    self.label_mouseover.world = ''
                else:
                    self.label_mouseover.world = f'{celestial_coordinates:32s} (ICRS)'
            else:
                self.label_mouseover.world = ''

            # Extract data values at this position.
            # TODO: for now we just use the first visible layer but we should think
            # of how to display values when multiple datasets are present.
            if x > -0.5 and y > -0.5 and x < image.shape[1] - 0.5 and y < image.shape[0] - 0.5:
                attribute = visible_layers[0].attribute
                value = image.get_data(attribute)[int(round(y)), int(round(x))]
                unit = image.get_component(attribute).units
                self.label_mouseover.value = f'{value:+10.5e} {unit}'
            else:
                self.label_mouseover.value = ''

        elif data['event'] == 'mouseleave' or data['event'] == 'mouseenter':

            self.label_mouseover.pixel = ""
            self.label_mouseover.world = ""
            self.label_mouseover.value = ""

        if data['event'] == 'keydown' and data['key'] == 'b':

            # Simple blinking of images - this will make it so that only one
            # layer is visible at a time and cycles through the layers.

            if len(self.state.layers) > 1:

                # If only one layer is visible, pick the next one to be visible,
                # otherwise start from the last visible one.

                visible = [ilayer for ilayer, layer in
                           enumerate(self.state.layers) if layer.visible]

                if len(visible) > 0:
                    next_layer = (visible[-1] + 1) % len(self.state.layers)
                    self.state.layers[next_layer].visible = True
                    for ilayer in visible:
                        if ilayer != next_layer:
                            self.state.layers[ilayer].visible = False

    def set_plot_axes(self):
        self.figure.axes[1].tick_format = None
        self.figure.axes[0].tick_format = None

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[0].label = "x: pixels"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"

    def data(self, cls=None):
        return [layer_state.layer  # .get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]
