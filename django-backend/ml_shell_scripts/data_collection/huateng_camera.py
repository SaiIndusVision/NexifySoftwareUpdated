import logging
import platform

import numpy as np

from data_collection.mvsdk import mvsdk
logger = logging.getLogger(__name__)

class HuaTengCamera(object):
    def __init__(self, config_file: str):
        super().__init__()
        self.config_file = config_file
        self.h_camera = None
        self.p_frame_buffer = None
        self.image_callback_function = None

    def set_image_callback(self, callback: callable):
        self.image_callback_function = callback
        
    def set_error_callback(self, callback: callable):
        self.error_callback_function = callback

    def initialise(self) -> bool:
        # Disable camera reconnection time out flag
        mvsdk.CameraSetSysOption('ReconnTimeLimit', 'disable')

        # Enumerates available devices
        device_list = mvsdk.CameraEnumerateDevice()
        if not device_list:
            logger.error('No camera was found!')
            raise ValueError('No camera was found!')

        # Select camera based on serial number
        selected_cam_index = -1
        for i, device_info in enumerate(device_list):
            logger.info(f'{i}: {device_info.GetFriendlyName()} {device_info.GetPortType()}')
            if self.camera_serial == device_info.GetSn():
                selected_cam_index = i

        device_info = device_list[selected_cam_index]
        logger.info(f'Selected device: {device_info.GetFriendlyName()}')

        # Initialise camera handle and load camera configuration file
        try:
            self.h_camera = mvsdk.CameraInit(device_info, -1, -1)
            mvsdk.CameraReadParameterFromFile(self.h_camera, self.config_file)
        except mvsdk.CameraException as e:
            logger.error(f'CameraInit Failed({e.error_code}): {e.message}')
            raise ValueError(f'CameraInit Failed({e.error_code}): {e.message}')

        # Choose if it is monochrome or colour camera.
        cap = mvsdk.CameraGetCapability(self.h_camera)
        mono_camera = cap.sIspCapacity.bMonoSensor != 0
        output_format = mvsdk.CAMERA_MEDIA_TYPE_MONO8 if mono_camera else mvsdk.CAMERA_MEDIA_TYPE_BGR8
        mvsdk.CameraSetIspOutFormat(self.h_camera, output_format)

        # Start camera 
        mvsdk.CameraPlay(self.h_camera)

        # Set up camera buffer
        frame_buffer_size = cap.sResolutionRange.iWidthMax * cap.sResolutionRange.iHeightMax * (1 if mono_camera else 3)
        self.p_frame_buffer = mvsdk.CameraAlignMalloc(frame_buffer_size, 16)

        # Set callaback for frame receival
        mvsdk.CameraSetCallbackFunction(self.h_camera, self.grab_callback, 0)

        # Set callback to receive info connection/diconnection
        mvsdk.CameraSetConnectionStatusCallback(self.h_camera, self.connection_status_callback, 0)

        return True

    @mvsdk.method(mvsdk.CAMERA_SNAP_PROC)
    def grab_callback(self, h_camera, p_raw_data, p_frame_head, p_context):
        frame_head = p_frame_head[0]
        # Process raw image using camera's image processing capabilities
        mvsdk.CameraImageProcess(h_camera, p_raw_data, self.p_frame_buffer, frame_head)
        mvsdk.CameraReleaseImageBuffer(h_camera, p_raw_data)

        if platform.system() == 'Windows':
            mvsdk.CameraFlipFrameBuffer(self.p_frame_buffer, frame_head, 1)

        # Convert processed data into numpy array for further manipulation
        frame_data = (mvsdk.c_ubyte * frame_head.uBytes).from_address(self.p_frame_buffer)
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = frame.reshape((frame_head.iHeight, frame_head.iWidth, 1 if frame_head.uiMediaType == mvsdk.CAMERA_MEDIA_TYPE_MONO8 else 3))

        # Pass frame to user-provided callback function
        if self.image_callback_function:
            self.image_callback_function(frame)

    @mvsdk.method(mvsdk.CAMERA_CONNECTION_STATUS_CALLBACK)
    def connection_status_callback(self, h_camera, msg, u_param, p_context):
        if msg == 0:
            logger.warning(f'Camera {h_camera} disconnected!')
            self.error_callback_function(ValueError(f'Camera {h_camera} disconnected!'))
        elif msg == 1:
            logger.info(f'Camera {h_camera} reconnected!')
            if u_param == 0:
                logger.info('Last drop reason: Network communication failure.')
            elif u_param == 1:
                logger.info('Last drop reason: Camera power loss.')

    def terminate(self):
        if self.h_camera:
            mvsdk.CameraUnInit(self.h_camera)
        if self.p_frame_buffer:
            mvsdk.CameraAlignFree(self.p_frame_buffer)
        logger.info('Camera terminated and resources released.')