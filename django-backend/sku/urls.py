# sku/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SKUViewSet,SKUImagesViewSet,SKUListImages,TagsViewSet,VersionsViewSet,LabelsViewSet,AnnotationViewSet,CameraImageCaptureViewset,DataSetViewset,DatasetSplitViewSet,ScriptRunnerViewSet,FinalDataSet,TrainingRunnerViewSet,TestResultsViewSet,TestResultsFolderViewSet,TestRunnerViewSet,FileExplorerViewSet,ModelFileExplorerViewSet,VersionDuplicateViewSet,ImageStreamViewSet,stream_page_view,stream_images_view,TrainingProgressViewSet,stream_progress_view,stream_page,TestingProgressViewset,stream_test_progress_view
router = DefaultRouter()
router.register('sku', SKUViewSet, basename='sku')
router.register('sku-images', SKUImagesViewSet, basename='sku-images')
router.register('sku-images-list',SKUListImages,basename="skuimagenames")
router.register('tags',TagsViewSet,basename='Tags')
router.register('versions',VersionsViewSet,basename='Version')
router.register('label',LabelsViewSet,basename="Labels")
router.register('annotations', AnnotationViewSet, basename='annotation')
router.register('capture-images', CameraImageCaptureViewset, basename='capture-images')
router.register('data-set',DataSetViewset, basename='dataset')
router.register('split-data-set', DatasetSplitViewSet, basename='split-dataset')
router.register("ai-camera",ScriptRunnerViewSet, basename="ai-camera")
router.register('final-data-set',FinalDataSet, basename='final-dataset')
router.register('train-runner', TrainingRunnerViewSet, basename='train-runner')
router.register('test-runner', TestRunnerViewSet, basename='test-runner')
router.register('test-results',TestResultsViewSet,basename='test-results')
router.register('test-results-folder', TestResultsFolderViewSet, basename='test-results-folder')
router.register('file-explorer', FileExplorerViewSet, basename='file-explorer')
router.register('model-explorer',ModelFileExplorerViewSet, basename='model-explorer')
router.register('version-duplicate',VersionDuplicateViewSet, basename='version-duplicate')
router.register('stream-image', ImageStreamViewSet, basename='stream-image')
router.register(r'training-progress', TrainingProgressViewSet, basename='training-progress')
router.register(r'testing-progress', TestingProgressViewset, basename='testing-progress')

urlpatterns = [
    path('', include(router.urls)),
    path('stream/', stream_page_view, name='stream-page'),
    path('capture-images-stream/', stream_images_view, name='stream-images'),
    path('stream-page/', stream_page, name='stream-progress'),
    path('stream-training-progress/', stream_progress_view, name='stream-training-progress'),
    path('stream-testing-progress/', stream_test_progress_view, name='stream-testing-progress'),

]