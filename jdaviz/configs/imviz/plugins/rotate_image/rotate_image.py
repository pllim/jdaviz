import numpy as np
from traitlets import Any

from jdaviz.configs.imviz.wcs_utils import generate_rotated_wcs
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, DatasetSelectMixin

__all__ = ['RotateImageSimple']


@tray_registry('imviz-rotate-image', label="Simple Image Rotation")
class RotateImageSimple(PluginTemplateMixin, DatasetSelectMixin):
    template_file = __file__, "rotate_image.vue"

    angle = Any(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._orig_wcs_key = '_orig_wcs'
        self._theta = 0  # degrees, clockwise

    def vue_rotate_image(self, *args, **kwargs):
        # We only grab the value here to avoid constantly updating as
        # user is still entering or updating the value.
        try:
            self._theta = float(self.angle)
        except Exception:
            return

        w_data = self.dataset.selected_dc_item.coords
        if w_data is None:  # Nothing to do
            return

        try:
            # Adjust the fake WCS to data with desired orientation.
            w_shape = self.dataset.selected_dc_item.shape
            w_in = generate_rotated_wcs(self._theta, shape=w_shape)

            # TODO: How to make this more robust?
            # Match with selected data.
            sky0 = w_data.pixel_to_world(0, 0)
            sky1 = w_data.pixel_to_world(w_shape[1] * 0.5, w_shape[0] * 0.5)
            avg_cdelt = (abs(sky1.ra.deg - sky0.ra.deg) + abs(sky1.dec.deg - sky0.dec.deg)) * 0.5
            w_in.wcs.crval = np.array([sky1.ra.deg, sky1.dec.deg])
            w_in.wcs.cdelt = np.array([-avg_cdelt, avg_cdelt])
            w_in.wcs.set()

            # FIXME: This does not work -- We did not rotate the data.
            # Store the original WCS, if not already.
            if self._orig_wcs_key not in self.dataset.selected_dc_item.meta:
                self.dataset.selected_dc_item.meta[self._orig_wcs_key] = self.dataset.selected_dc_item.coords  # noqa: E501

            # Update the WCS.
            self.dataset.selected_dc_item.coords = w_in

        except Exception as err:  # pragma: no cover
            self.hub.broadcast(SnackbarMessage(
                f"Image rotation failed: {repr(err)}", color='error', sender=self))

    def vue_reset_image(self, *args, **kwargs):
        w_data = self.dataset.selected_dc_item.coords
        if w_data is None:  # Nothing to do
            return

        try:
            if self._orig_wcs_key in self.dataset.selected_dc_item.meta:
                self.dataset.selected_dc_item.coords = self.dataset.selected_dc_item.meta[self._orig_wcs_key]  # noqa: E501

        except Exception as err:  # pragma: no cover
            self.hub.broadcast(SnackbarMessage(
                f"Image rotation reset failed: {repr(err)}", color='error', sender=self))
