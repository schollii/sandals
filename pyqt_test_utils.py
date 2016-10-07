# Use, distribution and modification of this file is bound by the terms of the MIT (expat) license. 

"""
Various testing utilities for PyQt. 
"""

__author__ = "Oliver Schoenborn"
__license__ = "MIT"
__version__ = '0.9.0'

__all__ = ['check_widget_snapshot']


# Discussion of check_widget_snapshot() is at 
# http://www.codeproject.com/Tips/1134902/Testing-QWidget-Snapshot-Regression-in-PyQt.
def check_widget_snapshot(widget: QWidget, ref_path: str, fig_name: str,
                          rms_tol_perc: float = 0.0, num_tol_perc: float=100.0) -> bool:
    """
    Get the difference between a widget's appearance and a file stored on disk. If the file doesn't
    exist, the file is created.
    :param widget: the widget for which appearance must be verified
    :param ref_path: the path to folder containing reference image (can be a file name too, then the
        parent is used as folder -- useful for tests where __file__ can be passed)
    :param fig_name: the name of the reference image (will be saved in ref_path folder if it doesn't
        exist, or read if it does)
    :param rms_tol_perc: percentage difference allowed between widget's snapshot and the reference, i.e.
        a floating point value in range 0..100
    :param num_tol_perc: the maximum percentage of mismatched pixels allowed, relative to total number
        of pixels in the reference image; two pixels differ if any of their R, G, B and A values differ
    :return: True if reference didn't exist (and was hence generated); True if widget matches reference;
        True if not matched but RMS diff is less than rms_tol_perc % and number of different pixels
        &lt; max_num_diffs; False otherwise

    Example use:

        # file some_test.py in folder 'testing'
        app = QApplication([])
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'label', rms_tol_perc=0.5, num_tol_perc=4)

    The first time the test is run, it will save a snapshot of the widget to label.png in 
    Path(__file__).parent and return True. The next time it is run, the widget snapshot will be compared 
    to the image saved. If the image colors have changed by more than 0.5% when averaged over all pixels, 
    or if more than 4% of pixels have changed in any way, check_widget_snapshot() will save a snapshot 
    of the widget to label_actual.png and the difference image to label_diff.png and will return False, 
    thus causing the test to fail. Otherwise (no differences, or differences within stated bounds), 
    check_widget_snapshot() will just return True and the test will pass.
    """
    actual_pixmap = widget.grab()
    image = actual_pixmap.toImage()
    rms_tol_perc = float(rms_tol_perc)  # ensure FPV so logging can format
    num_tol_perc = float(num_tol_perc)  # ensure FPV so logging can format

    ref_path = Path(ref_path)
    if ref_path.is_file():
        ref_path = ref_path.parent
    assert ref_path.is_dir()
    ref_pixmap_path = (ref_path / fig_name).with_suffix('.png')
    if not ref_pixmap_path.exists():
        # ref doesn't exist, generate it:
        log.info('Generating ref snapshot %s in %s for widget %s',
                 ref_pixmap_path.name, ref_pixmap_path.parent, widget)
        actual_pixmap.save(str(ref_pixmap_path))
        return True

    ref_pixmap = QPixmap(str(ref_pixmap_path))
    ref_image = ref_pixmap.toImage()
    if ref_image == image:
        return True

    diff_image = QImage(ref_image.width(), ref_image.height(), ref_image.format())
    DIFF_REF_PIX = 255  # value corresponds to "no difference"
    DIFF_MAX = 255
    REF_RGBA = [DIFF_REF_PIX] * 4
    diff_rms = 0
    num_diffs = 0
    for i in range(ref_image.width()):
        for j in range(ref_image.height()):
            pixel = image.pixelColor(i, j).getRgb()
            ref_pixel = ref_image.pixelColor(i, j).getRgb()
            if pixel != ref_pixel:
                diff = [pow((x - y) / DIFF_MAX, 2) for x, y in zip(pixel, ref_pixel)]
                diff_rms += sqrt(sum(diff) / len(pixel))
                diff = [DIFF_REF_PIX - abs(x - y) for x, y in zip(pixel, ref_pixel)]
                diff_image.setPixelColor(i, j, QColor(*diff))
                num_diffs += 1
            else:
                diff_image.setPixelColor(i, j, QColor(*REF_RGBA))

    total_num_pixels = ref_image.width() * ref_image.height()
    diff_rms /= total_num_pixels
    # use the following instead, for possibly improved representation of average difference over 
    # differing pixels:
    # diff_rms /= num_diffs 
    diff_rms_perc = diff_rms * 100
    num_diffs_perc = num_diffs * 100 / total_num_pixels
    log.info("Widget %s vs ref %s in %s:",
             widget.objectName() or repr(widget), ref_pixmap_path.name, ref_pixmap_path.parent)
    log.info("    RMS diff=%s%% (rms_tol_perc=%s%%), # pixels changed=%s%% (num_tol_perc=%s%%)",
             diff_rms_perc, rms_tol_perc, num_diffs_perc, num_tol_perc)

    if diff_rms_perc &lt;= rms_tol_perc and num_diffs_perc &lt;= num_tol_perc:
        return True

    # save the data

    actual_pix_path = ref_pixmap_path.with_name(fig_name + '_actual.png')
    log.warn("    Snapshot has changed beyond tolerances, saving actual and diff images to folder %s:",
             actual_pix_path.parent)
    actual_pixmap.save(str(actual_pix_path))

    diff_pix_path = ref_pixmap_path.with_name(fig_name + '_diff.png')
    assert actual_pix_path.parent == diff_pix_path.parent
    diff_pixmap = QPixmap(diff_image)
    diff_pixmap.save(str(diff_pix_path))

    log.warn("    Actual image saved to %s", actual_pix_path.name)
    log.warn("    White - |ref - widget| image saved to %s", diff_pix_path.name)

    return False
