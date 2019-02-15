from pathlib import Path
from os import remove
from PIL import Image, ImageDraw


class GifProgressBar:
    line_wide = 4  # 进度条宽度
    loop_playback = True  # 循环播放
    gif_type = 'C'  # 默认gif后一帧覆盖前一帧
    memory_mode = False  # 仅使用内存作为缓存
    cover_original = False  # 覆盖源文件
    auto_analysis = False  # 自动分析gif帧关系,gif_type设置无效

    def __init__(self, gif_path):
        self.gif_path = Path(gif_path)
        self._path_checker()
        self.memory_frame_list = []

        if self.auto_analysis:
            self._gif_type_analyze()

    def _path_checker(self):
        if self.gif_path.exists():
            if not self.memory_mode:
                self.temp_path = self.gif_path.parent / 'gif_progress_bar_temp'
                Path.mkdir(self.temp_path, exist_ok=True)
        else:
            raise OSError(f'{self.gif_path}文件不存在')

    def _gif_type_analyze(self):
        # 判断gif帧与帧之间的关系,帧之间叠加为C,每帧之间独立为F
        with open(self.gif_path, 'rb') as gif:
            current_im = Image.open(gif)
            self.size = current_im.size
            self.gif_type = 'F'
            try:
                while True:
                    if current_im.tile:
                        # current_im.tile ('gif', (0, 0, 618, 345), 819, (8, False))
                        frame_size = current_im.tile[0][1]  # (0, 0, 618, 345)
                        # print(tile, frame_size, current_im.size)
                        # current_im.size (618,345)
                        if frame_size[2:] != current_im.size:
                            self.gif_type = 'C'  # gif帧之间为叠加模式
                            print('C mode')
                            break
                    current_im.seek(current_im.tell() + 1)
            except EOFError:
                pass

    def gif_to_frame(self):
        gif_type, memory_mode = self.gif_type, self.memory_mode
        frame_list = self.memory_frame_list

        with open(self.gif_path, 'rb') as g:
            gif = Image.open(g)
            size = gif.size
            self.size = size

            palette = gif.getpalette()
            if palette:
                gif.putpalette(palette)  # 如果图片自带色板则使用自带的

            prev_frame = gif.convert('RGBA')  # 第一帧肯定是完整的
            try:
                while True:
                    frame_count = gif.tell()
                    current_frame = Image.new('RGBA', size)  # 新建帧对象

                    if gif_type == 'C':
                        # 如果帧之间的关系是覆盖,那么就需要当前帧覆盖在上一帧之上
                        current_frame.paste(prev_frame)
                    current_frame.paste(gif, (0, 0), gif.convert('RGBA'))

                    if memory_mode:
                        # 不使用缓存的情况下,直接在内存中保留Image对象
                        frame_list.append(current_frame)
                    else:
                        # 使用缓存的情况下,在内存中保留缓存的路径
                        current_frame_path = self.temp_path / f'{str(frame_count)}.png'
                        frame_list.append(current_frame_path)
                        current_frame.save(current_frame_path, 'PNG', quality=100)

                    prev_frame = current_frame  # 如果是覆盖模式,则下一帧需要当前帧当做底图
                    gif.seek(frame_count + 1)
            except EOFError:
                pass

    @staticmethod
    def _step_calculate(frame_count, wide):
        return 1 / (frame_count - 1) * wide

    def _image_draw(self, bar_high):
        # 画进度条函数
        line_wide = self.line_wide
        bar_high -= line_wide - 1
        memory_mode = self.memory_mode

        def __image_draw(bar_length, im_path_or_obj):
            if memory_mode:
                im = im_path_or_obj
            else:
                with im_path_or_obj.open('rb') as f:
                    im = Image.open(f)
                    im = im.convert('RGBA')

            draw = ImageDraw.Draw(im)
            draw.line((0, bar_high, bar_length, bar_high), fill='red', width=line_wide)
            # print(bar_length)
            # print(im)
            if not memory_mode:
                im.save(im_path_or_obj)

        def set_bar_high(x):
            nonlocal bar_high
            bar_high = x

        def get_bar_high():
            nonlocal bar_high
            return bar_high

        __image_draw.get_bar_high = get_bar_high
        __image_draw.set_bar_high = set_bar_high
        return __image_draw

    def frame_handler(self):
        w, h = self.size
        step = self._step_calculate(len(self.memory_frame_list), w)
        dr = self._image_draw(h)
        dr.set_bar_high = self.line_wide
        for index, current_frame_obj in enumerate(self.memory_frame_list):
            dr(round(step * index), current_frame_obj)

    def _clean_temp(self):
        memory_frame_list = self.memory_frame_list
        if not self.memory_mode:
            for path in memory_frame_list:
                remove(path)
            remove(self.temp_path)

    def make_gif(self):
        # 生成gif
        new_path = '{}'.format(self.gif_path.with_name('_' + self.gif_path.name)) \
            if not self.cover_original else self.gif_path
        loop = 0 if self.loop_playback else 1

        if not self.memory_mode:
            images_obj = [Image.open(im_path) for im_path in self.memory_frame_list]
        else:
            images_obj = self.memory_frame_list

        # 合成所有帧
        images_obj[0].save(new_path,
                           save_all=True,
                           append_images=images_obj[1::],
                           loop=loop,
                           quality=100)

        self._clean_temp()

    @classmethod
    def config(cls, line_wide=4,
               loop_playback=True,
               memory_mode=True,
               cover_original=False,
               auto_analysis=False):

        cls.line_wide = line_wide
        cls.loop_playback = loop_playback
        cls.memory_mode = memory_mode
        cls.cover_original = cover_original
        cls.auto_analysis = auto_analysis

    def start(self):
        self.gif_to_frame()  # gif 转帧序列
        self.frame_handler()  # 处理帧序列
        self.make_gif()  # 保存gif


class Gif_progress_bar_factory:
    def __init__(self, path):
        self.path = Path(path)
        self.handler = GifProgressBar

    def _gif_list(self) -> list:
        return [i for i in self.path.glob('*.gif')]

    def factory_config(self, line_wide=4,
                       loop_playback=True,
                       memory_mode=True,
                       cover_original=False,
                       auto_analysis=False):

        config = {'line_wide': line_wide,
                  'loop_playback': loop_playback,
                  'memory_mode': memory_mode,
                  'cover_original': cover_original,
                  'auto_analysis': auto_analysis}

        self.handler.config(**config)

    def gif_process(self):
        for gif in self._gif_list():
            g = self.handler(gif)
            g.start()


if __name__ == '__main__':
    # p = 'E:/test/test2.gif'
    # Gif_progress_bar(p).start()

    gf = Gif_progress_bar_factory('E:/test/')
    gf.factory_config(memory_mode=True)
    gf.gif_process()
