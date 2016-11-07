import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel

import pyqt_test_utils
from pyqt_test_utils import check_widget_snapshot, ImgDiffer


def non_existent_path(name: str):
    path = Path(name)
    if path.exists():
        path.unlink()
    assert not path.exists()
    return path


class TestCaseChecker:
    def setup_class(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

    def test1_gen_first_image(self):
        ref_image_path = non_existent_path('test1_gen_first_image.png')

        files_before = set(Path(__file__).parent.glob('*'))
        widget = QLabel('test')
        check_widget_snapshot(widget, __file__, str(ref_image_path))

        assert ref_image_path.exists()
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_after.difference(files_before) == set([ref_image_path.resolve()])

        ref_image_path.unlink()

    def test_log_and_ref_folder_instead_of_file(self):
        ref_image_path = non_existent_path('test_ref_folder_instead_of_file.png')

        folder = Path(__file__).parent
        files_before = set(folder.glob('*'))
        widget = QLabel('test')
        log = Mock()
        check_widget_snapshot(widget, str(folder), str(ref_image_path), log=log)

        assert ref_image_path.exists()
        assert log.info.call_args == call('Generating ref snapshot %s in %s for widget %s',
                                          'test_ref_folder_instead_of_file.png',
                                          folder, widget)
        files_after = set(folder.glob('*'))
        assert files_after.difference(files_before) == set([ref_image_path.resolve()])
        assert files_after.issuperset(files_before)

        ref_image_path.unlink()

    def test2_old_results(self):
        ref_image_path = non_existent_path('test2_old_results.png')

        # create two bogus files that pretend to be previous results:
        actual_img_path = Path('test2_old_results_actual.png')
        actual_img_path.write_text('')
        diff_img_path = Path('test2_old_results_diff.png')
        diff_img_path.write_text('')
        assert actual_img_path.exists()
        assert diff_img_path.exists()

        # check widget snapshot, with delete-old = False, verify results files still there:
        files_before = set(Path(__file__).parent.glob('*'))
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test2_old_results', delete_old_results=False)
        ref_image_path.unlink()
        assert actual_img_path.exists()
        assert diff_img_path.exists()
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_after == files_before

        # check it again, this time results removed:
        actual_img_path_str = actual_img_path.resolve()
        diff_img_path_str = diff_img_path.resolve()
        assert check_widget_snapshot(widget, __file__, 'test2_old_results')
        ref_image_path.unlink()
        assert not actual_img_path.exists()
        assert not diff_img_path.exists()
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_before.difference(files_after) == set([actual_img_path_str, diff_img_path_str])
        assert files_before.issuperset(files_before)

    def test_equal_images(self):
        ref_image_path = non_existent_path('test_equal_images.png')

        # generate reference:
        files_before = set(Path(__file__).parent.glob('*'))
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test_equal_images')

        # re-check: should find images are identical:
        assert check_widget_snapshot(widget, __file__, 'test_equal_images')
        assert check_widget_snapshot(widget, __file__, 'test_equal_images')
        ref_image_path.unlink()
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_before == files_after

    def test_unequal_images_diff_less_than_tol(self):
        ref_image_path = non_existent_path('test_unequal_images_diff_less_than_tol.png')

        class ImgDiffer_SameWithinTol:
            def get_diff(self, image, ref_image):
                return None

            def report(self):
                return "report"

        # generate reference:
        files_before = set(Path(__file__).parent.glob('*'))
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test_unequal_images_diff_less_than_tol')

        # pretend label has changed, but less than tolerance (get_diff() returns None):
        widget = QLabel('test2')
        widget.setObjectName('label')
        mock_log = Mock()
        assert check_widget_snapshot(widget, __file__, 'test_unequal_images_diff_less_than_tol',
                                     img_differ=ImgDiffer_SameWithinTol(), log=mock_log)
        ref_image_path.unlink()
        assert mock_log.method_calls == [
            call.info('Widget %s vs ref %s in %s:',
                      'label', 'test_unequal_images_diff_less_than_tol.png', ref_image_path.parent.resolve()),
            call.info('    report')
        ]
        # confirm that no results files were created:
        files_after = set(Path(__file__).parent.glob('*'))
        assert files_after == files_before

    def test_unequal_images(self):
        ref_image_path = non_existent_path('test_unequal_images.png')

        class ImgDiffer:
            def get_diff(self, image, ref_image):
                return QImage(image)

            def report(self):
                return "report"

        # generate reference:
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test_unequal_images')

        # pretend label has changed, but less than tolerance (get_diff() returns None):
        widget = QLabel('test2')
        widget.setObjectName('label')
        mock_log = Mock()
        files_before = set(Path(__file__).parent.glob('*'))
        assert not check_widget_snapshot(widget, __file__, 'test_unequal_images',
                                         img_differ=ImgDiffer(), log=mock_log)
        assert mock_log.method_calls == [
            call.info('Widget %s vs ref %s in %s:', 'label', 'test_unequal_images.png',
                      ref_image_path.parent.resolve()),
            call.info('    report'),
            call.warn('    Snapshot has changed beyond tolerances, saving actual and diff images to folder %s:',
                      ref_image_path.parent.resolve()),
            call.warn('    Saving actual image to %s', 'test_unequal_images_actual.png'),
            call.warn('    Saving diff image (White - |ref - widget|) to %s', 'test_unequal_images_diff.png')
        ]
        # confirm that no results files were create:
        files_after = set(Path(__file__).parent.glob('*'))
        ref_image_path.unlink()
        assert files_after.issuperset(files_before)
        actual_img_path = Path('test_unequal_images_actual.png')
        diff_img_path = Path('test_unequal_images_diff.png')
        assert files_after.difference(files_before) == set([actual_img_path.resolve(), diff_img_path.resolve()])
        actual_img_path.unlink()
        diff_img_path.unlink()

    def test_custom_differ(self):
        ref_image_path = non_existent_path('test_custom_differ.png')

        # generate reference:
        widget = QLabel('test')
        assert check_widget_snapshot(widget, __file__, 'test_custom_differ')

        # pretend label has changed, but less than tolerance (get_diff() returns None):
        widget = QLabel('test2')
        widget.setObjectName('label')

        # first check that kwargs when custom differ given causes exception:
        img_differ = Mock()
        img_differ.get_diff.return_value=None
        pytest.raises(ValueError,
                      check_widget_snapshot, widget, __file__, 'test_custom_differ',
                      img_differ=img_differ, kwarg1=1, kwarg2=2)
        assert check_widget_snapshot(widget, __file__, 'test_custom_differ', img_differ=img_differ)
        assert len(img_differ.method_calls) == 1
        assert img_differ.get_diff.call_count == 1

        img_differ_class = Mock()
        img_differ_class.return_value.get_diff.return_value=None
        with patch.object(pyqt_test_utils, 'ImgDiffer', img_differ_class) as mock_default_differ:
            assert check_widget_snapshot(widget, __file__, 'test_custom_differ')
            assert mock_default_differ.call_args_list == [call()]

        ref_image_path.unlink()


class TestCaseImgDiffer:

    def setup_class(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

    def test_same(self):
        widget1 = QLabel('test1')
        widget2 = QLabel('test1')
        ref_img = widget1.grab().toImage()
        img = widget2.grab().toImage()
        assert img == ref_img

        differ = ImgDiffer()
        differ.get_diff(img, ref_img)

    def test_same_size(self):
        widget1 = QLabel('test1')
        widget2 = QLabel('test2')

        def test():
            widget2.show()
            widget1.setFixedSize(widget2.width(), widget2.height())
            widget1.show()

            ref_img = widget1.grab().toImage()
            img = widget2.grab().toImage()
            assert img != ref_img
            assert img.size() == ref_img.size()

            differ = ImgDiffer()
            diff = differ.get_diff(img, ref_img)
            expect = QPixmap('same_size.png')
            assert expect.toImage() == diff

            self.app.closeAllWindows()

        QTimer.singleShot(0, test)
        self.app.exec()

    def test_wider(self):
        widget1 = QLabel('test1')
        widget2 = QLabel('test23456')

        def test():
            widget1.show()
            widget2.show()

            ref_img = widget1.grab().toImage()
            img = widget2.grab().toImage()
            assert img != ref_img
            assert img.width() != ref_img.width()
            assert img.height() == ref_img.height()

            differ = ImgDiffer()
            diff = differ.get_diff(img, ref_img)
            # QPixmap(ref_img).save('wider_ref.png')
            # QPixmap(img).save('wider_actual.png')
            # QPixmap(diff).save('wider_diff.png')
            expect = QPixmap('wider_diff.png')
            assert expect.toImage() == diff

            self.app.closeAllWindows()

        QTimer.singleShot(0, test)
        self.app.exec()

