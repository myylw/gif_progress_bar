from pathlib import Path
from PIL import Image, ImageDraw
from abc import ABCMeta, abstractmethod


class FramesHandle(metaclass=ABCMeta):
    @abstractmethod
    def frames_handle(self, frames: list):
        pass


class GifObject:
    def __init__(self, gif_path=None, frame_list=None):
        self.gif_path = self._path_check(gif_path)
        self.frame_list = frame_list if frame_list else []
        self.gif_size = (0, 0)

    @staticmethod
    def _path_check(gif_path):
        if gif_path:
            path = Path(gif_path)
            if path.exists():
                return path
            else:
                raise OSError(f'{gif_path}文件不存在')
        else:
            return None

    def get_frame_list(self) -> list:
        if self.frame_list:
            return self.frame_list

        with open(self.gif_path, 'rb') as gif_file:
            gif = Image.open(gif_file)
            self.gif_size = gif.size

            palette = gif.getpalette()
            if palette:
                gif.putpalette(palette)

            prev_frame = gif.convert('RGBA')
            try:
                while True:
                    frame_count = gif.tell()
                    current_frame = Image.new('RGBA', self.gif_size)  # 新建帧对象
                    current_frame.paste(prev_frame)
                    current_frame.paste(gif, (0, 0), gif.convert('RGBA'))

                    self.frame_list.append(current_frame)
                    prev_frame = current_frame  # 下一帧需要当前帧当做底图
                    gif.seek(frame_count + 1)
            except EOFError:
                pass

            return self.frame_list

    @staticmethod
    def save_gif(frames, save_path, quality=100):
        if frames:
            frames[0].save(save_path,
                           save_all=True,
                           append_images=frames[1::],
                           loop=0,
                           quality=quality
                           )
            del frames


class GifProcessor:
    def __init__(self, gif_path):
        self.gif_path = Path(gif_path)
        self.gif_obj = GifObject(gif_path)
        self.handles = []
        self.frames = None

    def handle_register(self, handle: FramesHandle):
        self.handles.append(handle)

    def start_handle(self):
        self.frames = self.gif_obj.get_frame_list()

        if not self.handles:
            raise RuntimeWarning("没有注册帧处理函数")

        for handle in self.handles:
            handle.frames_handle(self.frames)
        self._gif_save()

    def _save_path(self):
        return '{}'.format(self.gif_path.with_name('_' + self.gif_path.name))

    def _gif_save(self):
        self.gif_obj.save_gif(self.frames, self._save_path())


class MultipleGifProcessor:
    def __init__(self, folder_path):
        self.folder_path = Path(folder_path)
        self.handles = []

    def get_path_list(self):
        return [i for i in filter(lambda path: not path.name.startswith('_'), self.folder_path.glob('*.gif'))]

    def handle_register(self, handle: FramesHandle):
        self.handles.append(handle)

    def start_handle(self):
        if not self.handles:
            raise RuntimeWarning("没有注册帧处理函数")

        for gif in self.get_path_list():
            gif_obj = GifProcessor(gif)
            gif_obj.handles = self.handles
            gif_obj.start_handle()


class ProcessBarHandle(FramesHandle):
    def __init__(self, line_height=None, line_color="red"):
        self.line_height = line_height
        self.line_color = line_color

    @staticmethod
    def _step_calculate(frame_count, gif_wide):
        return 1 / (frame_count - 1) * gif_wide

    @staticmethod
    def _get_size(frames: list):
        size = frames[0].size
        return size[0], size[1]

    @staticmethod
    def _self_adaption_bar_height(frame_height):
        return int(frame_height * 0.015)

    def _frame_draw(self, frame_height):
        bar_height = self._self_adaption_bar_height(frame_height) if self.line_height is None else self.line_height
        bar_y_point = frame_height - self._self_adaption_bar_height(frame_height) // 2
        color = self.line_color

        def __frame_draw(image, bar_x_point):
            draw = ImageDraw.Draw(image)
            draw.line((0, bar_y_point, bar_x_point, bar_y_point), fill=color, width=bar_height)

        return __frame_draw

    def frames_handle(self, frames: list):
        w, h = self._get_size(frames)
        step = self._step_calculate(len(frames), w)
        frame_draw = self._frame_draw(h)
        for index in range(len(frames)):
            frame_draw(frames[index], round(step * index))


class CompressedSizeHandle(FramesHandle):
    def __init__(self, size=None, percent=None):
        self.size = size if size is not None else (128, 128)
        self.percent = percent

    @staticmethod
    def _get_size(frames: list):
        size = frames[0].size
        return size[0], size[1]

    def frames_handle(self, frames: list):
        w, h = self._get_size(frames)
        nw, nh = int(w * self.percent), int(h * self.percent) if self.percent is not None else self.size
        for frame in frames:
            frame.thumbnail((nw, nh))


if __name__ == '__main__':
    m = MultipleGifProcessor('E:/test/')
    m.handle_register(ProcessBarHandle(line_color='yellow'))
    m.handle_register(CompressedSizeHandle(percent=0.5))
    m.start_handle()
