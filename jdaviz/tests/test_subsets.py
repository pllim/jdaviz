import numpy as np
import pytest
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from astropy.utils.data import get_pkg_data_filename
from glue.core.roi import CircularROI, CircularAnnulusROI, EllipticalROI, RectangularROI, XRangeROI
from glue.core.subset_group import GroupedSubset
from glue.core.edit_subset_mode import AndMode, AndNotMode, NewMode, OrMode, XorMode
from regions import (PixCoord, CirclePixelRegion, CircleSkyRegion, RectanglePixelRegion,
                     EllipsePixelRegion, CircleAnnulusPixelRegion)
from numpy.testing import assert_allclose
from specutils import SpectralRegion, Spectrum1D
from astropy.nddata import NDData

from jdaviz.utils import get_subset_type, MultiMaskSubsetState


def test_region_from_subset_2d(cubeviz_helper):
    cubeviz_helper.load_data(np.ones((128, 128, 1)), data_label='Test 2D Flux')

    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')

    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test 2D Flux')

    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(EllipticalROI(1, 3.5, 1.2, 3.3))

    subsets = cubeviz_helper.app.get_subsets()
    reg = subsets.get('Subset 1')[0]['region']

    assert len(subsets) == 1
    assert isinstance(reg, EllipsePixelRegion)

    assert_allclose(reg.center.x, 1)
    assert_allclose(reg.center.y, 3.5)
    assert_allclose(reg.width, 2.4)
    assert_allclose(reg.height, 6.6)
    assert_allclose(reg.angle.value, 0)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ["EllipticalROI"]
    assert subset_plugin.is_centerable
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "X Center (pixels)", key) == 1
        assert subset_plugin._get_value_from_subset_definition(0, "Y Center (pixels)", key) == 3.5
        assert subset_plugin._get_value_from_subset_definition(0, "X Radius (pixels)", key) == 1.2
        assert subset_plugin._get_value_from_subset_definition(0, "Y Radius (pixels)", key) == 3.3
        assert subset_plugin._get_value_from_subset_definition(0, "Angle", key) == 0

    # Recenter GUI should not be exposed, but API call would raise exception.
    with pytest.raises(NotImplementedError, match='Cannot recenter'):
        subset_plugin.vue_recenter_subset()


def test_region_from_subset_3d(cubeviz_helper):
    cubeviz_helper.load_data(np.ones((128, 128, 256)), data_label='Test 3D Flux')

    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.subset_selected == "Create New"

    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test 3D Flux')

    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    subsets = cubeviz_helper.app.get_subsets()
    reg = cubeviz_helper.app.get_subsets('Subset 1', object_only=True)[0]

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)
    assert_allclose(reg.angle.value, 0)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ["RectangularROI"]
    assert subset_plugin.is_centerable
    assert subset_plugin.get_center() == (2.25, 1.55)
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Xmin (pixels)", key) == 1
        assert subset_plugin._get_value_from_subset_definition(0, "Xmax (pixels)", key) == 3.5
        assert subset_plugin._get_value_from_subset_definition(0, "Ymin (pixels)", key) == -0.2
        assert subset_plugin._get_value_from_subset_definition(0, "Ymax (pixels)", key) == 3.3
        assert subset_plugin._get_value_from_subset_definition(0, "Angle", key) == 0

    # Mimic user changing something in Subset Tool GUI.
    subset_plugin._set_value_in_subset_definition(0, "Xmin (pixels)", "value", 2)
    subset_plugin._set_value_in_subset_definition(0, "Ymin (pixels)", "value", 0)
    subset_plugin._set_value_in_subset_definition(0, "Angle", "value", 45)  # ccw deg
    # "orig" is unchanged until user clicks Update button.
    assert subset_plugin._get_value_from_subset_definition(0, "Xmin (pixels)", "orig") == 1
    assert subset_plugin._get_value_from_subset_definition(0, "Ymin (pixels)", "orig") == -0.2
    assert subset_plugin._get_value_from_subset_definition(0, "Angle", "orig") == 0
    subset_plugin.vue_update_subset()
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Xmin (pixels)", key) == 2
        assert subset_plugin._get_value_from_subset_definition(0, "Xmax (pixels)", key) == 3.5
        assert subset_plugin._get_value_from_subset_definition(0, "Ymin (pixels)", key) == 0
        assert subset_plugin._get_value_from_subset_definition(0, "Ymax (pixels)", key) == 3.3
        assert subset_plugin._get_value_from_subset_definition(0, "Angle", key) == 45

    subsets = cubeviz_helper.app.get_subsets()
    reg = subsets.get('Subset 1')[0]['region']

    assert_allclose(reg.center.x, 2.75)
    assert_allclose(reg.center.y, 1.65)
    assert_allclose(reg.width, 1.5)
    assert_allclose(reg.height, 3.3)
    assert_allclose(reg.angle.to_value(u.deg), 45)  # Might be stored in radians

    # Move the rectangle
    subset_plugin.set_center((3, 2), update=True)
    subsets = cubeviz_helper.app.get_subsets()
    reg = subsets.get('Subset 1')[0]['region']
    assert_allclose(reg.center.x, 3)
    assert_allclose(reg.center.y, 2)
    assert_allclose(reg.width, 1.5)
    assert_allclose(reg.height, 3.3)
    assert_allclose(reg.angle.to_value(u.deg), 45)  # Might be stored in radians

    # Circular Subset
    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    # We set the active tool here to trigger a reset of the Subset state to "Create New"
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['bqplot:truecircle']
    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=3, yc=4, radius=2.4))
    assert subset_plugin.subset_selected == "Subset 2"
    assert subset_plugin.subset_types == ["CircularROI"]
    assert subset_plugin.is_centerable
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "X Center (pixels)", key) == 3
        assert subset_plugin._get_value_from_subset_definition(0, "Y Center (pixels)", key) == 4
        assert subset_plugin._get_value_from_subset_definition(0, "Radius (pixels)", key) == 2.4

    # Circular Annulus Subset
    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    # We set the active tool here to trigger a reset of the Subset state to "Create New"
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['bqplot:circannulus']
    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularAnnulusROI(xc=5,
                                                                              yc=6,
                                                                              inner_radius=2,
                                                                              outer_radius=4))
    assert subset_plugin.subset_selected == "Subset 3"
    assert subset_plugin.subset_types == ["CircularAnnulusROI"]
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "X Center (pixels)", key) == 5
        assert subset_plugin._get_value_from_subset_definition(0, "Y Center (pixels)", key) == 6
        assert subset_plugin._get_value_from_subset_definition(0, "Inner Radius (pixels)", key) == 2
        assert subset_plugin._get_value_from_subset_definition(0, "Outer Radius (pixels)", key) == 4


def test_region_from_subset_profile(cubeviz_helper, spectral_cube_wcs):
    data = Spectrum1D(flux=np.ones((128, 128, 256)) * u.nJy, wcs=spectral_cube_wcs)
    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')

    cubeviz_helper.load_data(data, data_label='Test 1D Flux')

    cubeviz_helper.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(5, 15.5))

    subsets = cubeviz_helper.app.get_subsets(spectral_only=True)
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, SpectralRegion)
    assert_quantity_allclose(reg.lower, 5.0 * u.Hz)
    assert_quantity_allclose(reg.upper, 15.5 * u.Hz)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ["Range"]
    assert subset_plugin.is_centerable
    assert_allclose(subset_plugin.get_center(), 10.25)
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", key) == 5
        assert subset_plugin._get_value_from_subset_definition(0, "Upper bound", key) == 15.5

    # Mimic user changing something in Subset Tool GUI.
    subset_plugin._set_value_in_subset_definition(0, "Lower bound", "value", 10)
    # "orig" is unchanged until user clicks Update button.
    assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", "orig") == 5
    subset_plugin.vue_update_subset()
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", key) == 10
        assert subset_plugin._get_value_from_subset_definition(0, "Upper bound", key) == 15.5

    subsets = cubeviz_helper.app.get_subsets(spectral_only=True)
    reg = subsets.get('Subset 1')

    assert_quantity_allclose(reg.lower, 10.0 * u.Hz)
    assert_quantity_allclose(reg.upper, 15.5 * u.Hz)

    # Move the Subset.
    subset_plugin.set_center(10, update=True)
    subsets = cubeviz_helper.app.get_subsets(spectral_only=True)
    reg = subsets.get('Subset 1')
    assert_quantity_allclose(reg.lower, 7.25 * u.Hz)
    assert_quantity_allclose(reg.upper, 12.75 * u.Hz)


def test_disjoint_spectral_subset(cubeviz_helper, spectral_cube_wcs):
    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    data = Spectrum1D(flux=np.ones((128, 128, 256)) * u.nJy, wcs=spectral_cube_wcs)
    cubeviz_helper.load_data(data, data_label="Test Flux")

    spec_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")
    spec_viewer.apply_roi(XRangeROI(5, 15.5))

    # Add second region to Subset 1
    cubeviz_helper.app.session.edit_subset_mode.mode = OrMode
    spec_viewer.apply_roi(XRangeROI(30, 35))

    reg = cubeviz_helper.app.get_subsets('Subset 1')

    assert len(reg) == 2
    assert isinstance(reg, SpectralRegion)
    assert_quantity_allclose(reg[0].lower, 5.0*u.Hz)
    assert_quantity_allclose(reg[0].upper, 15.5*u.Hz)
    assert_quantity_allclose(reg[1].lower, 30.0*u.Hz)
    assert_quantity_allclose(reg[1].upper, 35.0*u.Hz)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ["Range", "Range"]
    assert subset_plugin.glue_state_types == ["RangeSubsetState", "OrState"]

    # Make sure that certain things are not possible because we are
    # dealing with a composite spectral subset
    subset_plugin.set_center(99, update=True)   # This is no-op
    assert subset_plugin.get_center() is None

    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(1, "Lower bound", key) == 30
        assert subset_plugin._get_value_from_subset_definition(1, "Upper bound", key) == 35
        assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", key) == 5
        assert subset_plugin._get_value_from_subset_definition(0, "Upper bound", key) == 15.5

    # We will now update one of the bounds of the composite subset
    subset_plugin._set_value_in_subset_definition(1, "Lower bound", "value", 25)
    subset_plugin.vue_update_subset()
    assert subset_plugin._get_value_from_subset_definition(1, "Lower bound", "value") == 25
    assert subset_plugin._get_value_from_subset_definition(1, "Lower bound", "orig") == 25

    reg = cubeviz_helper.app.get_subsets('Subset 1')
    assert_quantity_allclose(reg[1].lower, 25.0*u.Hz)  # It is now the updated value


def test_composite_region_from_subset_3d(cubeviz_helper):
    cubeviz_helper.load_data(np.ones((128, 128, 10)), data_label='Test 3D Flux')

    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test 3D Flux')
    viewer = cubeviz_helper.app.get_viewer('flux-viewer')

    viewer.apply_roi(CircularROI(xc=25, yc=25, radius=5))
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    circle1 = CirclePixelRegion(center=PixCoord(x=25, y=25), radius=5)
    assert reg[-1] == {'name': 'CircularROI', 'glue_state': 'RoiSubsetState', 'region': circle1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    cubeviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(RectangularROI(25, 30, 25, 30))
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    rectangle1 = RectanglePixelRegion(center=PixCoord(x=27.5, y=27.5),
                                      width=5, height=5, angle=0.0 * u.deg)
    assert reg[-1] == {'name': 'RectangularROI', 'glue_state': 'AndNotState', 'region': rectangle1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    cubeviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(EllipticalROI(xc=30, yc=30, radius_x=3, radius_y=6))
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    ellipse1 = EllipsePixelRegion(center=PixCoord(x=30, y=30),
                                  width=6, height=12, angle=0.0 * u.deg)
    assert reg[-1] == {'name': 'EllipticalROI', 'glue_state': 'OrState', 'region': ellipse1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    cubeviz_helper.app.session.edit_subset_mode.mode = AndMode
    viewer.apply_roi(RectangularROI(20, 25, 20, 25))
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    rectangle2 = RectanglePixelRegion(center=PixCoord(x=22.5, y=22.5),
                                      width=5, height=5, angle=0.0 * u.deg)
    assert reg[-1] == {'name': 'RectangularROI', 'glue_state': 'AndState', 'region': rectangle2,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    cubeviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(CircularROI(xc=21, yc=24, radius=1))
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    circle2 = CirclePixelRegion(center=PixCoord(x=21, y=24), radius=1)
    assert reg[-1] == {'name': 'CircularROI', 'glue_state': 'AndNotState', 'region': circle2,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ['CircularROI', 'RectangularROI', 'EllipticalROI',
                                          'RectangularROI', 'CircularROI']
    assert subset_plugin.glue_state_types == ['AndState', 'AndNotState',
                                              'OrState', 'AndState', 'AndNotState']


def test_composite_region_with_consecutive_and_not_states(cubeviz_helper):
    cubeviz_helper.load_data(np.ones((128, 128, 10)), data_label='Test 3D Flux')

    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test 3D Flux')
    viewer = cubeviz_helper.app.get_viewer('flux-viewer')

    viewer.apply_roi(CircularROI(xc=25, yc=25, radius=5))
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    circle1 = CirclePixelRegion(center=PixCoord(x=25, y=25), radius=5)
    assert reg[-1] == {'name': 'CircularROI', 'glue_state': 'RoiSubsetState', 'region': circle1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    cubeviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(RectangularROI(25, 30, 25, 30))
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    rectangle1 = RectanglePixelRegion(center=PixCoord(x=27.5, y=27.5),
                                      width=5, height=5, angle=0.0 * u.deg)
    assert reg[-1] == {'name': 'RectangularROI', 'glue_state': 'AndNotState', 'region': rectangle1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    cubeviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(EllipticalROI(xc=30, yc=30, radius_x=3, radius_y=6))
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    ellipse1 = EllipsePixelRegion(center=PixCoord(x=30, y=30),
                                  width=6, height=12, angle=0.0 * u.deg)
    assert reg[-1] == {'name': 'EllipticalROI', 'glue_state': 'AndNotState', 'region': ellipse1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    regions_list = cubeviz_helper.app.get_subsets("Subset 1", object_only=True)
    assert len(regions_list) == 3
    assert regions_list[-1].width == 6

    regions_list = cubeviz_helper.app.get_subsets("Subset 1", spatial_only=True,
                                                  object_only=True)
    assert len(regions_list) == 3
    assert regions_list[-1].width == 6

    spatial_list = cubeviz_helper.app.get_subsets("Subset 1", spatial_only=True)
    assert len(spatial_list) == 3

    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ['CircularROI', 'RectangularROI', 'EllipticalROI']
    assert subset_plugin.glue_state_types == ['AndState', 'AndNotState', 'AndNotState']

    # This should be prevented since radius must be positive
    subset_plugin._set_value_in_subset_definition(0, "Radius", "value", 0)
    subset_plugin.vue_update_subset()

    # This should also be prevented since a rectangle must have positive width
    # and length
    subset_plugin._set_value_in_subset_definition(1, "Xmin", "value", 0)
    subset_plugin._set_value_in_subset_definition(1, "Xmax", "value", 0)
    subset_plugin.vue_update_subset()

    # Make sure changes were not propagated
    reg = cubeviz_helper.app.get_subsets("Subset 1")
    assert reg[0]['subset_state'].roi.radius == 5
    assert reg[1]['subset_state'].roi.xmin == 25
    assert reg[1]['subset_state'].roi.xmax == 30

    for layer in viewer.state.layers:
        if isinstance(layer.layer, GroupedSubset):
            assert get_subset_type(layer.layer.subset_state) == 'spatial'


def test_composite_region_with_imviz(imviz_helper, image_2d_wcs):
    arr = NDData(np.ones((10, 10)), wcs=image_2d_wcs)

    data_label = 'image-data'
    viewer = imviz_helper.default_viewer._obj
    imviz_helper.load_data(arr, data_label=data_label, show_in_viewer=True)
    viewer.apply_roi(CircularROI(xc=5, yc=5, radius=2))
    reg = imviz_helper.app.get_subsets("Subset 1")
    circle1 = CirclePixelRegion(center=PixCoord(x=5, y=5), radius=2)
    assert reg[-1] == {'name': 'CircularROI', 'glue_state': 'RoiSubsetState', 'region': circle1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    imviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(RectangularROI(xmin=2, xmax=4, ymin=2, ymax=4))
    reg = imviz_helper.app.get_subsets("Subset 1")
    rectangle1 = RectanglePixelRegion(center=PixCoord(x=3, y=3),
                                      width=2, height=2, angle=0.0 * u.deg)
    assert reg[-1] == {'name': 'RectangularROI', 'glue_state': 'AndNotState', 'region': rectangle1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    imviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(EllipticalROI(xc=3, yc=3, radius_x=3, radius_y=6))
    reg = imviz_helper.app.get_subsets("Subset 1")
    ellipse1 = EllipsePixelRegion(center=PixCoord(x=3, y=3),
                                  width=6, height=12, angle=0.0 * u.deg)
    assert reg[-1] == {'name': 'EllipticalROI', 'glue_state': 'AndNotState', 'region': ellipse1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    imviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(CircularAnnulusROI(xc=5, yc=5, inner_radius=2.5, outer_radius=5))
    reg = imviz_helper.app.get_subsets("Subset 1")
    ann1 = CircleAnnulusPixelRegion(center=PixCoord(x=5, y=5), inner_radius=2.5, outer_radius=5)
    assert reg[-1] == {'name': 'CircularAnnulusROI', 'glue_state': 'OrState', 'region': ann1,
                       'sky_region': None, 'subset_state': reg[-1]['subset_state']}

    subset_plugin = imviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ['CircularROI', 'RectangularROI', 'EllipticalROI',
                                          'CircularAnnulusROI']
    assert subset_plugin.glue_state_types == ['AndState', 'AndNotState', 'AndNotState', 'OrState']


def test_recenter_linked_by_wcs(imviz_helper):
    """Similar test case as TestAdvancedAperPhot.
    Images are only aligned if linked by WCS.
    """
    # Reference image
    imviz_helper.load_data(get_pkg_data_filename(
        'data/gauss100_fits_wcs.fits', package='jdaviz.configs.imviz.tests'))
    # Different pixel scale
    imviz_helper.load_data(get_pkg_data_filename(
        'data/gauss100_fits_wcs_block_reduced.fits', package='jdaviz.configs.imviz.tests'))

    # Link them by WCS
    imviz_helper.link_data(align_by='wcs')
    w = imviz_helper.app.data_collection[0].coords

    # This rectangle is over a real object in reference image but
    # only the last row in the second image if linked by pixel.
    imviz_helper.load_regions(
        RectanglePixelRegion(center=PixCoord(x=229, y=152), width=17, height=7).to_sky(w))

    subset_plugin = imviz_helper.plugins["Subset Tools"]._obj
    subset_plugin.subset_selected = "Subset 1"
    subset_plugin.dataset_selected = "gauss100_fits_wcs_block_reduced[PRIMARY,1]"

    # Do it a few times to converge.
    for _ in range(5):
        subset_plugin.vue_recenter_subset()

    # If handled correctly, it won't change much.
    # But if not, it move down by 7 pix or so (229.05, 145.92) and fails the test.
    xy = imviz_helper.default_viewer._obj._get_real_xy(
        imviz_helper.app.data_collection[0], *subset_plugin.get_center())[:2]
    assert_allclose(xy, (229.067822, 152.371943))

    # Now create a new subset that has a source in the corner and test
    # recentering with multiselect.

    imviz_helper.load_regions(
        CirclePixelRegion(center=PixCoord(x=145, y=175), radius=17).to_sky(w))
    subset_plugin.multiselect = True
    subset_plugin.subset_selected = ["Subset 1", "Subset 2"]

    # Do it a few times to converge.
    for _ in range(5):
        subset_plugin.vue_recenter_subset()

    xy = imviz_helper.default_viewer._obj._get_real_xy(
        imviz_helper.app.data_collection[0], *subset_plugin.get_center("Subset 2"))[:2]
    assert_allclose(xy, (145.593022, 172.515541))

    with pytest.raises(ValueError, match="Please include subset_name in"):
        subset_plugin.get_center()
    with pytest.raises(ValueError, match="Please include subset_name in"):
        subset_plugin.set_center((150, 200))


def test_with_invalid_subset_name(cubeviz_helper):
    subset_name = "Test"
    with pytest.raises(ValueError, match=f'{subset_name} not in '):
        cubeviz_helper.app.get_subsets(subset_name=subset_name)


def test_composite_region_from_subset_2d(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    viewer = specviz_helper.app.get_viewer(specviz_helper._default_spectrum_viewer_reference_name)
    viewer.apply_roi(XRangeROI(6000, 7000))
    reg = specviz_helper.app.get_subsets("Subset 1", simplify_spectral=False)
    subset1 = SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                             7000 * spectrum1d.spectral_axis.unit)
    assert reg[-1]['region'].lower == subset1.lower and reg[-1]['region'].upper == subset1.upper
    assert reg[-1]['glue_state'] == 'RangeSubsetState'

    specviz_helper.app.session.edit_subset_mode.mode = AndNotMode

    viewer.apply_roi(XRangeROI(6500, 6800))
    reg = specviz_helper.app.get_subsets("Subset 1", simplify_spectral=False)
    subset1 = SpectralRegion(6500 * spectrum1d.spectral_axis.unit,
                             6800 * spectrum1d.spectral_axis.unit)
    assert reg[-1]['region'].lower == subset1.lower and reg[-1]['region'].upper == subset1.upper
    assert reg[-1]['glue_state'] == 'AndNotState'

    specviz_helper.app.session.edit_subset_mode.mode = OrMode

    viewer.apply_roi(XRangeROI(7200, 7800))
    reg = specviz_helper.app.get_subsets("Subset 1", simplify_spectral=False)
    subset1 = SpectralRegion(7200 * spectrum1d.spectral_axis.unit,
                             7800 * spectrum1d.spectral_axis.unit)
    assert reg[-1]['region'].lower == subset1.lower and reg[-1]['region'].upper == subset1.upper
    assert reg[-1]['glue_state'] == 'OrState'

    specviz_helper.app.session.edit_subset_mode.mode = AndMode

    viewer.apply_roi(XRangeROI(6800, 7500))
    reg = specviz_helper.app.get_subsets("Subset 1", simplify_spectral=False)
    subset1 = SpectralRegion(6800 * spectrum1d.spectral_axis.unit,
                             7500 * spectrum1d.spectral_axis.unit)
    assert reg[-1]['region'].lower == subset1.lower and reg[-1]['region'].upper == subset1.upper
    assert reg[-1]['glue_state'] == 'AndState'

    subset_plugin = specviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ['Range', 'Range', 'Range', 'Range']
    assert subset_plugin.glue_state_types == ['AndState', 'AndNotState', 'OrState', 'AndState']

    subset_plugin.vue_simplify_subset()
    assert subset_plugin.glue_state_types == ["RangeSubsetState", "OrState"]

    for layer in viewer.state.layers:
        if isinstance(layer.layer, GroupedSubset):
            assert get_subset_type(layer.layer.subset_state) == 'spectral'


def test_edit_composite_spectral_subset(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    viewer = specviz_helper.app.get_viewer(specviz_helper._default_spectrum_viewer_reference_name)

    viewer.apply_roi(XRangeROI(6200, 6800))
    specviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(7200, 7600))

    specviz_helper.app.session.edit_subset_mode.mode = XorMode
    viewer.apply_roi(XRangeROI(6200, 7600))

    reg = specviz_helper.app.get_subsets("Subset 1")
    assert reg.lower.value == 6800 and reg.upper.value == 7200

    subset_plugin = specviz_helper.app.get_tray_item_from_name('g-subset-plugin')

    # We will now update one of the bounds of the composite subset
    subset_plugin._set_value_in_subset_definition(0, "Lower bound", "value", 6000)
    subset_plugin.vue_update_subset()

    # Since we updated one of the Range objects and it's lower bound
    # is now lower than the XOR region bound, the region from 6000 to
    # 6200 should now be visible in the viewer.
    reg = specviz_helper.app.get_subsets("Subset 1")
    assert reg[0].lower.value == 6000 and reg[0].upper.value == 6200
    assert reg[1].lower.value == 6800 and reg[1].upper.value == 7200

    # This makes it so that only spectral regions within this bound
    # are visible, so the API should reflect that.
    specviz_helper.app.session.edit_subset_mode.mode = AndMode
    viewer.apply_roi(XRangeROI(6600, 7400))

    reg = specviz_helper.app.get_subsets("Subset 1")
    assert reg.lower.value == 6800 and reg[0].upper.value == 7200

    # This should be prevented by the _check_inputs method
    subset_plugin._set_value_in_subset_definition(0, "Lower bound", "value", 8000)
    subset_plugin.vue_update_subset()
    reg2 = specviz_helper.app.get_subsets("Subset 1")
    assert reg.lower.value == reg2.lower.value
    assert reg.upper.value == reg2.upper.value

    assert subset_plugin.can_simplify

    viewer.apply_roi(XRangeROI(7800, 8000))
    with pytest.raises(ValueError, match="AND mode should overlap with existing subset"):
        specviz_helper.app.get_subsets("Subset 1")


def test_composite_spectral_with_xor(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    viewer = specviz_helper.app.get_viewer(specviz_helper._default_spectrum_viewer_reference_name)

    viewer.apply_roi(XRangeROI(6200, 6800))
    specviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(7200, 7600))

    specviz_helper.app.session.edit_subset_mode.mode = XorMode
    viewer.apply_roi(XRangeROI(6100, 7600))
    reg = specviz_helper.app.get_subsets("Subset 1")

    assert reg[0].lower.value == 6100 and reg[0].upper.value == 6200
    assert reg[1].lower.value == 6800 and reg[1].upper.value == 7200

    specviz_helper.app.session.edit_subset_mode.mode = NewMode
    viewer.apply_roi(XRangeROI(7000, 7200))
    specviz_helper.app.session.edit_subset_mode.mode = XorMode
    viewer.apply_roi(XRangeROI(7100, 7300))
    specviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(6900, 7105))
    reg = specviz_helper.app.get_subsets("Subset 2")
    assert reg[0].lower.value == 6900 and reg[0].upper.value == 7105
    assert reg[1].lower.value == 7200 and reg[1].upper.value == 7300

    specviz_helper.app.session.edit_subset_mode.mode = NewMode
    viewer.apply_roi(XRangeROI(6000, 6500))
    specviz_helper.app.session.edit_subset_mode.mode = XorMode
    viewer.apply_roi(XRangeROI(6100, 6200))
    reg = specviz_helper.app.get_subsets("Subset 3")
    assert reg[0].lower.value == 6000 and reg[0].upper.value == 6100
    assert reg[1].lower.value == 6200 and reg[1].upper.value == 6500

    specviz_helper.app.session.edit_subset_mode.mode = NewMode
    viewer.apply_roi(XRangeROI(6100, 6200))
    specviz_helper.app.session.edit_subset_mode.mode = XorMode
    viewer.apply_roi(XRangeROI(6000, 6500))
    reg = specviz_helper.app.get_subsets("Subset 4")
    assert reg[0].lower.value == 6000 and reg[0].upper.value == 6100
    assert reg[1].lower.value == 6200 and reg[1].upper.value == 6500

    specviz_helper.app.session.edit_subset_mode.mode = NewMode
    viewer.apply_roi(XRangeROI(7500, 7600))
    specviz_helper.app.session.edit_subset_mode.mode = XorMode
    viewer.apply_roi(XRangeROI(6000, 6010))
    reg = specviz_helper.app.get_subsets("Subset 5")
    assert reg[0].lower.value == 6000 and reg[0].upper.value == 6010
    assert reg[1].lower.value == 7500 and reg[1].upper.value == 7600


def test_composite_spectral_with_xor_complicated(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    viewer = specviz_helper.app.get_viewer(specviz_helper._default_spectrum_viewer_reference_name)

    viewer.apply_roi(XRangeROI(6100, 6700))

    # (6100, 6200), (6300, 6700)
    specviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(XRangeROI(6200, 6300))

    # (6050, 6100), (6200, 6300), (6700, 6800)
    specviz_helper.app.session.edit_subset_mode.mode = XorMode
    viewer.apply_roi(XRangeROI(6050, 6800))

    # (6050, 6100), (6200, 6300), (6700, 6800), (7000, 7200)
    specviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(7000, 7200))

    # (6010, 6020), (6050, 6100), (6200, 6300), (6700, 6800), (7000, 7200)
    viewer.apply_roi(XRangeROI(6010, 6020))

    # (6010, 6020), (6050, 6090), (6100, 6200), (6300, 6700), (6800, 6850), (7000, 7200)
    specviz_helper.app.session.edit_subset_mode.mode = XorMode
    viewer.apply_roi(XRangeROI(6090, 6850))

    reg = specviz_helper.app.get_subsets("Subset 1")
    assert reg[0].lower.value == 6010 and reg[0].upper.value == 6020
    assert reg[1].lower.value == 6050 and reg[1].upper.value == 6090
    assert reg[2].lower.value == 6100 and reg[2].upper.value == 6200
    assert reg[3].lower.value == 6300 and reg[3].upper.value == 6700
    assert reg[4].lower.value == 6800 and reg[4].upper.value == 6850
    assert reg[5].lower.value == 7000 and reg[5].upper.value == 7200


def test_overlapping_spectral_regions(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    viewer = specviz_helper.app.get_viewer(specviz_helper._default_spectrum_viewer_reference_name)

    viewer.apply_roi(XRangeROI(6400, 7400))
    specviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(XRangeROI(6600, 7200))

    specviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(6600, 7300))

    subset_plugin = specviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.can_simplify
    subset_plugin.vue_simplify_subset()

    reg = specviz_helper.app.get_subsets("Subset 1")
    assert reg.lower.value == 6400 and reg.upper.value == 7400


def test_only_overlapping_spectral_regions(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    viewer = specviz_helper.app.get_viewer(specviz_helper._default_spectrum_viewer_reference_name)

    viewer.apply_roi(XRangeROI(6400, 6600))
    assert specviz_helper.app.is_there_overlap_spectral_subset("Subset 1") is False
    specviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(7000, 7400))

    viewer.apply_roi(XRangeROI(6600, 7300))

    viewer.apply_roi(XRangeROI(7600, 7800))

    subset_plugin = specviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.can_simplify
    subset_plugin.vue_simplify_subset()

    reg = specviz_helper.app.get_subsets("Subset 1")
    assert reg[0].lower.value == 6400 and reg[0].upper.value == 7400
    assert reg[1].lower.value == 7600 and reg[1].upper.value == 7800


def test_overlapping_in_specviz2d(specviz2d_helper, mos_spectrum2d):
    specviz2d_helper.load_data(spectrum_2d=mos_spectrum2d)
    viewer = specviz2d_helper.app.get_viewer(
        specviz2d_helper._default_spectrum_2d_viewer_reference_name)

    viewer.apply_roi(XRangeROI(6400, 7400))
    specviz2d_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(XRangeROI(6600, 7200))

    specviz2d_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(6600, 7300))

    subset_plugin = specviz2d_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.can_simplify
    subset_plugin.vue_simplify_subset()

    reg = specviz2d_helper.app.get_subsets("Subset 1")
    assert reg.lower.value == 6400 and reg.upper.value == 7400


def test_only_overlapping_in_specviz2d(specviz2d_helper, mos_spectrum2d):
    specviz2d_helper.load_data(spectrum_2d=mos_spectrum2d)
    viewer = specviz2d_helper.app.get_viewer(
        specviz2d_helper._default_spectrum_2d_viewer_reference_name)

    viewer.apply_roi(XRangeROI(6400, 6600))
    specviz2d_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(7000, 7400))

    viewer.apply_roi(XRangeROI(6600, 7300))

    viewer.apply_roi(XRangeROI(7600, 7800))

    subset_plugin = specviz2d_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.can_simplify
    subset_plugin.vue_simplify_subset()

    reg = specviz2d_helper.app.get_subsets("Subset 1")
    assert reg[0].lower.value == 6400 and reg[0].upper.value == 7400
    assert reg[1].lower.value == 7600 and reg[1].upper.value == 7800


def test_multi_mask_subset(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d)
    viewer = specviz_helper.app.get_viewer(specviz_helper._default_spectrum_viewer_reference_name)

    viewer.apply_roi(XRangeROI(6200, 6800))

    plugin = specviz_helper.app.get_tray_item_from_name("g-subset-plugin")
    plugin.can_freeze = True
    plugin.vue_freeze_subset()

    reg = specviz_helper.app.get_subsets()
    assert reg["Subset 1"][0]["region"] == 3
    assert isinstance(reg["Subset 1"][0]["subset_state"], MultiMaskSubsetState)

    specviz_helper.app.session.edit_subset_mode.mode = OrMode
    viewer.apply_roi(XRangeROI(7200, 7600))

    # Simplify subset ignores Mask subsets
    reg = specviz_helper.app.get_subsets()
    assert (reg["Subset 1"].lower.value == 7200
            and reg["Subset 1"].upper.value == 7600)

    # If we set simplify to False, we see all subregions
    reg = specviz_helper.app.get_subsets(simplify_spectral=False)
    assert (reg["Subset 1"][1]["region"].lower.value == 7200
            and reg["Subset 1"][1]["region"].upper.value == 7600)
    assert reg["Subset 1"][0]["region"] == 3
    assert plugin.can_simplify is False

    # If we freeze again, all subregions become a Mask subset object
    plugin.vue_freeze_subset()
    reg = specviz_helper.app.get_subsets()
    assert reg["Subset 1"][0]["region"] == 5

    # When freezing an AndNot state, the number of mask values should decrease
    specviz_helper.app.session.edit_subset_mode.mode = AndNotMode
    viewer.apply_roi(XRangeROI(6600, 7200))

    reg = specviz_helper.app.get_subsets(simplify_spectral=False)
    assert (reg["Subset 1"][1]["region"].lower.value == 6600
            and reg["Subset 1"][1]["region"].upper.value == 7200)
    assert reg["Subset 1"][0]["region"] == 5

    plugin.vue_freeze_subset()
    reg = specviz_helper.app.get_subsets()
    assert reg["Subset 1"][0]["region"] == 4


def test_delete_subsets(cubeviz_helper, spectral_cube_wcs):
    """
    Test that the toolbar selections get reset when the subset being actively edited gets deleted.
    """
    data = Spectrum1D(flux=np.ones((128, 128, 256)) * u.nJy, wcs=spectral_cube_wcs)
    cubeviz_helper.load_data(data, data_label="Test Flux")
    dc = cubeviz_helper.app.data_collection

    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")
    spectrum_viewer.toolbar.active_tool = spectrum_viewer.toolbar.tools['bqplot:xrange']
    spectrum_viewer.apply_roi(XRangeROI(5, 15.5))

    dc.remove_subset_group(dc.subset_groups[0])

    assert spectrum_viewer.toolbar.active_tool_id == "jdaviz:selectslice"

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    # We set the active tool here to trigger a reset of the Subset state to "Create New"
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['bqplot:rectangle']
    flux_viewer.apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    dc.remove_subset_group(dc.subset_groups[0])

    assert flux_viewer.toolbar.active_tool is None


class TestRegionsFromSubsets:
    """Tests for obtaining Sky Regions from subsets."""

    def test_get_regions_from_subsets_cubeviz(self, cubeviz_helper, spectral_cube_wcs):

        """ Basic tests for retrieving Sky Regions from spatial subsets in Cubeviz.
        """
        data = Spectrum1D(flux=np.ones((128, 128, 256)) * u.nJy, wcs=spectral_cube_wcs)
        cubeviz_helper.load_data(data)

        # basic test, a single circular region
        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(25, 25, 10))
        subsets = cubeviz_helper.app.get_subsets(include_sky_region=True)
        sky_region = subsets['Subset 1'][0]['sky_region']
        assert isinstance(sky_region, CircleSkyRegion)
        assert_allclose(sky_region.center.ra.deg, 24.40786313)
        assert_allclose(sky_region.center.dec.deg, 22.45185308)
        assert_allclose(sky_region.radius.arcsec, 28001.08106569353)

        # and that it is None when not specified
        subsets = cubeviz_helper.app.get_subsets()
        assert subsets['Subset 1'][0]['sky_region'] is None

        # now test a composite subset, each component should have a sky region
        cubeviz_helper.app.session.edit_subset_mode.mode = AndMode
        cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(30, 30, 10))

        subsets = cubeviz_helper.app.get_subsets(include_sky_region=True)
        assert len(subsets['Subset 1']) == 2
        sky_region_0 = subsets['Subset 1'][0]['sky_region']
        sky_region_1 = subsets['Subset 1'][1]['sky_region']
        assert_allclose(sky_region_0.center.ra.deg, 24.40786313)
        assert_allclose(sky_region_0.center.dec.deg, 22.45185308)
        assert_allclose(sky_region_0.radius.arcsec, 28001.08106569353)
        assert_allclose(sky_region_1.center.ra.deg, 28.41569583)
        assert_allclose(sky_region_1.center.dec.deg, 25.44814949)
        assert_allclose(sky_region_1.radius.arcsec, 25816.498273)

        # and that they are both None when not specified
        subsets = cubeviz_helper.app.get_subsets()
        assert subsets['Subset 1'][0]['sky_region'] is None
        assert subsets['Subset 1'][1]['sky_region'] is None

    def test_get_regions_from_subsets_imviz(self, imviz_helper, spectral_cube_wcs):

        """ Basic tests for retrieving Sky Regions from subsets in Imviz.
        """

        # using cube WCS instead of 2d imaging wcs for consistancy with
        # cubeviz test. accessing just the spatial part of this.
        wcs = spectral_cube_wcs.celestial

        data = NDData(np.ones((128, 128)) * u.nJy, wcs=wcs)
        imviz_helper.load_data(data)

        # basic test, a single circular region
        imviz_helper.app.get_viewer('imviz-0').apply_roi(CircularROI(25, 25, 10))
        subsets = imviz_helper.app.get_subsets(include_sky_region=True)
        sky_region = subsets['Subset 1'][0]['sky_region']
        assert isinstance(sky_region, CircleSkyRegion)
        assert_allclose(sky_region.center.ra.deg, 24.40786313)
        assert_allclose(sky_region.center.dec.deg, 22.45185308)
        assert_allclose(sky_region.radius.arcsec, 28001.08106569353)

        # now test a composite subset, each component should have a sky region
        imviz_helper.app.session.edit_subset_mode.mode = AndMode
        imviz_helper.app.get_viewer('imviz-0').apply_roi(CircularROI(30, 30, 10))

        subsets = imviz_helper.app.get_subsets(include_sky_region=True)
        assert len(subsets['Subset 1']) == 2
        sky_region_0 = subsets['Subset 1'][0]['sky_region']
        sky_region_1 = subsets['Subset 1'][1]['sky_region']
        assert_allclose(sky_region_0.center.ra.deg, 24.40786313)
        assert_allclose(sky_region_0.center.dec.deg, 22.45185308)
        assert_allclose(sky_region_0.radius.arcsec, 28001.08106569353)
        assert_allclose(sky_region_1.center.ra.deg, 28.41569583)
        assert_allclose(sky_region_1.center.dec.deg, 25.44814949)
        assert_allclose(sky_region_1.radius.arcsec, 25816.498273)

    def test_no_wcs_sky_regions(self, imviz_helper):

        """ Make sure that if sky regions are requested and there is no WCS,
            that it returns None with no error.
        """

        data = NDData(np.ones((40, 40)) * u.nJy)
        imviz_helper.load_data(data)

        imviz_helper.app.get_viewer('imviz-0').apply_roi(CircularROI(25, 25, 10))
        subsets = imviz_helper.app.get_subsets(include_sky_region=True)
        assert subsets['Subset 1'][0]['sky_region'] is None

    def test_subset_renaming(self, specviz_helper, spectrum1d):
        specviz_helper.load_data(spectrum1d, 'myfile')
        spectrum_viewer_name = specviz_helper._default_spectrum_viewer_reference_name
        viewer = specviz_helper.app.get_viewer(spectrum_viewer_name)

        viewer.apply_roi(XRangeROI(6200, 7200))
        get_data_no_sub = specviz_helper.get_data('myfile')
        get_data_1 = specviz_helper.get_data('myfile', spectral_subset='Subset 1')

        get_data_1_mask = np.where(~get_data_1.mask)

        # Retrieving data with no subset means mask is None
        assert get_data_no_sub.mask is None
        assert len(get_data_1_mask[0]) > 0

        # rename subset to 'diffname'
        subset_group = specviz_helper.app.data_collection.subset_groups
        subset_group[0].label = 'diffname'
        get_data_2 = specviz_helper.get_data('myfile', spectral_subset='diffname')

        assert_quantity_allclose(get_data_1.flux, get_data_2.flux)
        assert_quantity_allclose(get_data_1.spectral_axis, get_data_2.spectral_axis)
        get_data_2_mask = np.where(~get_data_2.mask)
        assert (get_data_1_mask[0] == get_data_2_mask[0]).all()

        # when we officially implement subset renaming in jdaviz, we will want
        # to be aware of the case of naming subsets after existing data
        # and handle it appropriately
        subset_group = specviz_helper.app.data_collection.subset_groups
        subset_group[0].label = 'myfile'
        get_data_3 = specviz_helper.get_data('myfile', spectral_subset='myfile')

        get_data_3_mask = np.where(~get_data_3.mask)
        assert (get_data_1_mask[0] == get_data_3_mask[0]).all()
