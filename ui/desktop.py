import asyncio, json, logging, shutil, time, os, threading
from pathlib import Path
from datetime import date, datetime
import flet as ft
from core.stream_resolver import extract_urls, QUALITIES
from core.monitor import Monitor
from storage.database import Store
from utils.runtime import data_dir, configure_logs, binary, open_path, export_diagnostics, autostart, VERSION

GREEN='#17835A'; INK='#1E302A'
def label(text,size=14,color=INK): return ft.Text(str(text),size=size,color=color)
def button(text,handler,primary=False): return ft.Button(text,on_click=handler,bgcolor=GREEN if primary else '#EAF0ED',color='white' if primary else INK)
def table(headers,rows):
    return ft.Row([ft.DataTable(columns=[ft.DataColumn(label(h)) for h in headers],rows=rows,column_spacing=22,heading_row_color='#EFF4F1')],scroll=ft.ScrollMode.AUTO)
def cell(text): return ft.DataCell(label(text))

class Desktop:
    def __init__(self,page,home=None):
        self.page=page; self.home=Path(home or data_dir()); configure_logs(self.home)
        self.store=Store(self.home/'livewatch.sqlite3'); self.monitor=Monitor(self.store,self.home/'Recordings')
        self.selected=0; self.query=''; self.tray=None; self.exiting=False; self.installing=False
        page.title='LiveWatch 直播观察助手'; page.theme_mode=ft.ThemeMode.LIGHT
        page.theme=ft.Theme(color_scheme_seed=GREEN,font_family='Microsoft YaHei')
        page.bgcolor='#F5F7F6'; page.padding=0; page.window.width=1180; page.window.height=760
        page.window.min_width=1000; page.window.min_height=650; page.window.prevent_close=True
        page.window.on_event=self.window_event
        self.body=ft.Column(expand=True,scroll=ft.ScrollMode.AUTO,spacing=18)
        self.banner=label('仅录制本人或已获授权的直播。退出软件或关机后录制会停止。',12,'#63756C')
        nav=ft.NavigationRail(selected_index=0,label_type=ft.NavigationRailLabelType.ALL,min_width=100,
            destinations=[ft.NavigationRailDestination(icon=icon,label=name) for icon,name in [(ft.Icons.LIVE_TV,'直播监控'),(ft.Icons.VIDEO_LIBRARY,'录像管理'),(ft.Icons.BAR_CHART,'数据统计'),(ft.Icons.SETTINGS,'软件设置')]],on_change=self.navigate)
        page.add(ft.Column([ft.Container(ft.Row([label('●  LiveWatch',24,GREEN),label('直播观察助手  ·  v'+VERSION,14),ft.Container(expand=True),label('本地存储 · 无需注册',12)]),padding=24,bgcolor='white'),ft.Row([nav,ft.VerticalDivider(width=1),ft.Container(self.body,padding=24,expand=True)],expand=True),ft.Container(self.banner,padding=12)],expand=True))
        self.render()
    def toast(self,text): self.page.show_dialog(ft.SnackBar(label(text)))
    def close_dialog(self,e=None): self.page.pop_dialog()
    async def navigate(self,e): self.selected=e.control.selected_index; self.render()
    def root(self): return Path(self.store.setting('directory',str(self.monitor.root)))
    def action(self,func,*args):
        async def run(e=None):
            try:
                result=func(*args)
                if asyncio.iscoroutine(result): await result
                self.render()
            except Exception as exc:
                logging.getLogger('livewatch.app').exception('界面操作失败'); self.toast(str(exc))
        return run
    def render(self):
        if self.exiting: return
        self.body.controls=[self.monitor_page,self.recordings_page,self.stats_page,self.settings_page][self.selected]()
        self.page.update()
    def monitor_page(self):
        tasks=self.store.tasks(); records=self.store.recordings(); today=date.today().isoformat()
        try: free=shutil.disk_usage(self.root()).free/1024**3
        except OSError: free=0
        cards=ft.Row([ft.Container(ft.Column([label(title,12,'#63756C'),label(value,26,GREEN)]),padding=18,bgcolor='white',border_radius=12,expand=True) for title,value in [('监控主播',len(tasks)),('正在录制',sum(s.process is not None and s.process.returncode is None for s in self.monitor.sessions.values())),('今日录制',sum(r['started'].startswith(today) for r in records)),('可用磁盘',f'{free:.1f} GB')]])
        rows=[]
        for t in tasks:
            i=t['id']; s=self.monitor.sessions.get(i); state=self.monitor.states.get(i,'已停止')
            name=ft.Column([label(t['name'] or '待获取主播'),label(t['note'] or t['url'],11,'#63756C'),label(t['group_name'],11)])
            operations=ft.Row([ft.TextButton('停止' if t['enabled'] else '启动',on_click=self.action(self.monitor.stop if t['enabled'] else self.monitor.start,i)),ft.TextButton('编辑',on_click=self.action(self.edit,t)),ft.TextButton('删除',on_click=self.action(self.delete_task,t))],spacing=0)
            rows.append(ft.DataRow(cells=[ft.DataCell(name),ft.DataCell(ft.Text(state,color=GREEN if state=='录制中' else INK,tooltip=self.monitor.details.get(i,''))),cell(next((k for k,v in QUALITIES.items() if v==t['quality']),t['quality'])),cell(f'{int(time.monotonic()-s.clock)//60} 分钟' if s else '—'),cell(f'{s.size()/1024**2:.1f} MB' if s else '—'),ft.DataCell(operations)]))
        return [cards,ft.Row([label('直播监控',22),ft.Container(expand=True),button('添加主播 / 批量添加',self.action(self.add_dialog),True),button('全部启动',self.action(self.monitor.start_all)),button('全部停止',self.action(self.monitor.stop_all))]),label('画质为请求档位，实际分辨率以录像检测为准。状态提示可悬停查看。',12,'#63756C'),table(['主播 / 备注 / 分组','直播状态','请求画质','录制时长','文件大小','操作'],rows) if rows else ft.Container(label('还没有主播。粘贴抖音直播链接，开始建立你的观察列表。',17),padding=40,bgcolor='white')]
    def add_dialog(self):
        field=ft.TextField(label='粘贴直播链接或分享文本，可多行批量添加',multiline=True,min_lines=4,width=620)
        authorized=ft.Checkbox(label='我确认有权录制这些直播内容',value=False)
        async def save(e):
            if not authorized.value: self.toast('请先确认录制授权'); return
            try: urls=extract_urls(field.value or '')
            except ValueError as exc: self.toast(str(exc)); return
            count=0; duplicates=0
            import sqlite3
            for url in urls:
                try: i=self.store.add(url,name='待获取主播'); self.monitor.start(i); count+=1
                except sqlite3.IntegrityError: duplicates+=1
            self.close_dialog(); self.render(); self.toast(f'已添加 {count} 个，重复 {duplicates} 个；后台获取主播信息')
        self.page.show_dialog(ft.AlertDialog(title=label('添加主播',21),content=ft.Column([field,authorized],tight=True),actions=[ft.TextButton('取消',on_click=self.close_dialog),button('添加并监控',save,True)]))
    def edit(self,t):
        note=ft.TextField(label='备注',value=t['note']); group=ft.TextField(label='分组',value=t['group_name'])
        quality=ft.Dropdown(label='请求画质',value=t['quality'],options=[ft.DropdownOption(key=v,text=k) for k,v in QUALITIES.items()])
        directory=ft.TextField(label='保存目录（留空使用默认目录）',value=t['directory'],width=600)
        async def save(e):
            was=bool(t['enabled']); await self.monitor.stop(t['id'])
            self.store.update(t['id'],note=note.value or '',group_name=group.value or '',quality=quality.value,directory=directory.value.strip())
            if was: self.monitor.start(t['id'])
            self.close_dialog(); self.render()
        self.page.show_dialog(ft.AlertDialog(title=label('编辑主播'),content=ft.Column([note,group,quality,directory,label('保存后会安全结束当前文件并重新监控。',12)],tight=True),actions=[ft.TextButton('取消',on_click=self.close_dialog),button('保存',self.action(save,None),True)]))
    def confirm(self,title,text,callback):
        async def yes(e):
            self.close_dialog(); await self.action(callback)()
        self.page.show_dialog(ft.AlertDialog(title=label(title,20),content=label(text),actions=[ft.TextButton('取消',on_click=self.close_dialog),button('确认',yes)]))
    def delete_task(self,t):
        async def remove():
            await self.monitor.stop(t['id']); self.store.execute('DELETE FROM tasks WHERE id=?',(t['id'],)); self.render()
        self.confirm('删除主播任务','将停止此任务，历史录像文件保留。',remove)
    def recordings_page(self):
        async def search(e): self.query=e.control.value or ''; self.render()
        rows=[]
        for r in self.store.recordings(self.query):
            actions=ft.Row([ft.TextButton('播放',on_click=self.action(self.play,r)),ft.TextButton('目录',on_click=self.action(open_path,r['path'],True)),ft.TextButton('删除',on_click=self.action(self.delete_record,r))],spacing=0)
            rows.append(ft.DataRow(cells=[cell(r['name']),ft.DataCell(ft.Text(r['title'] or '',max_lines=2,width=150,tooltip=r['title'])),cell(r['started']),cell(r['ended'] or '—'),cell(f"{(r['duration'] or 0)/60:.1f} 分"),cell(f"{(r['size'] or 0)/1024**2:.1f} MB"),cell(r['quality']),ft.DataCell(ft.Text(r['status'],tooltip=r['path'])),ft.DataCell(actions)]))
        return [label('录像管理',24),ft.TextField(label='按主播或日期搜索（回车）',value=self.query,on_submit=search,width=400),table(['主播','直播标题','开始时间','结束时间','实际时长','大小','请求画质','状态 / 路径','操作'],rows),label('一条记录对应一场监控录制会话；分段与断线续录文件位于同一目录。',12)]
    def play(self,r):
        meta=json.loads(Path(r['path']).read_text(encoding='utf-8'))
        files=meta.get('video_files') or [str(p) for p in Path(r['path']).parent.glob('*.ts')]
        if not files: raise RuntimeError('没有可播放文件')
        open_path(files[0])
    def delete_record(self,r):
        if r['id'] in [s.id for s in self.monitor.sessions.values()]: self.toast('请先停止此录制'); return
        actual=ft.Checkbox(label='同时删除此会话目录中的实际录像（不可恢复）',value=False)
        async def remove():
            if actual.value:
                directory=Path(r['path']).parent
                # Only delete enumerated files from this unique session; no recursive rmtree.
                meta=json.loads(Path(r['path']).read_text(encoding='utf-8'))
                if meta.get('session_id')!=r['id']: raise ValueError('录像身份不匹配，拒绝删除文件')
                for p in directory.iterdir():
                    if p.is_file() and p.suffix in ('.ts','.mp4'): p.unlink()
                Path(r['path']).unlink()
            self.store.execute('DELETE FROM recordings WHERE id=?',(r['id'],)); self.render()
        async def proceed(e):
            self.close_dialog()
            if actual.value: self.confirm('再次确认删除实际视频','此会话所有 TS/MP4 将永久删除，无法撤销。',remove)
            else: await self.action(remove)()
        self.page.show_dialog(ft.AlertDialog(title=label('删除录像记录'),content=actual,actions=[ft.TextButton('取消',on_click=self.close_dialog),button('继续',proceed)]))
    def stats_page(self):
        records=self.store.recordings(); days={}
        for r in records:
            key=r['started'][:10]; days.setdefault(key,[0,0,0]); days[key][0]+=1; days[key][1]+=r['duration'] or 0; days[key][2]+=r['size'] or 0
        return [label('数据统计',24),label('统计来自本地录制记录，不包含推测的在线人数、观看量或成交量。',13),label(f'累计 {len(records)} 场 · {sum(r[1] for r in days.values())/3600:.2f} 小时',25,GREEN),table(['日期','会话数','有效录像时长','存储大小'],[ft.DataRow(cells=[cell(k),cell(v[0]),cell(f'{v[1]/60:.1f} 分钟'),cell(f'{v[2]/1024**3:.2f} GB')]) for k,v in sorted(days.items(),reverse=True)])]
    def settings_page(self):
        interval=ft.TextField(label='监控间隔（秒，最少30）',value=str(self.store.setting('interval',120)),width=260)
        concurrency=ft.TextField(label='最大同时录制数量（1–20）',value=str(self.store.setting('concurrency',3)),width=260)
        segment=ft.Dropdown(label='分段录制',value=str(self.store.setting('segment_minutes',30)),options=[ft.DropdownOption(key='30',text='30 分钟'),ft.DropdownOption(key='60',text='60 分钟')],width=260)
        directory=ft.TextField(label='默认录像保存目录',value=str(self.root()),width=700)
        convert=ft.Checkbox(label='录制结束自动无损封装 MP4（失败时保留 TS）',value=self.store.setting('convert',False))
        delete=ft.Checkbox(label='MP4 校验成功后删除原始 TS',value=self.store.setting('delete_source',False))
        boot=ft.Checkbox(label='Windows 登录后启动（EXE 版本）',value=self.store.setting('autostart',False))
        async def save(e):
            try:
                iv=int(interval.value); co=int(concurrency.value)
                if not 30<=iv<=86400 or not 1<=co<=20: raise ValueError('间隔应为30–86400秒，并发应为1–20')
                p=Path(directory.value).expanduser().resolve(); p.mkdir(parents=True,exist_ok=True)
                if boot.value!=self.store.setting('autostart',False): autostart(boot.value)
                for k,v in dict(interval=iv,concurrency=co,segment_minutes=int(segment.value),directory=str(p),convert=convert.value,delete_source=delete.value,autostart=boot.value).items(): self.store.set_setting(k,v)
                self.toast('已保存。录制格式及目录设置在下次录制会话生效。')
            except Exception as exc: self.toast(str(exc))
        async def diagnostic(e):
            dest=self.home/('diagnostics_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip')
            await asyncio.to_thread(export_diagnostics,self.home,dest); self.toast('已导出：'+str(dest)); open_path(dest,True)
        deps='  |  '.join(n+('：已检测到' if binary(n) else '：缺失') for n in ('ffmpeg','ffprobe','node'))
        return [label('软件设置',24),ft.Row([interval,concurrency,segment]),directory,convert,delete,boot,button('保存设置',save,True),ft.Divider(),label('运行依赖',20),label(deps),label('将 ffmpeg.exe、ffprobe.exe、node.exe 放入软件旁 tools 文件夹，或安装到 PATH。\n本版本不分发这些二进制；从下方官方入口安装后重启软件。低于5GB自动停止。',13),ft.Row([ft.TextButton('FFmpeg 官方下载',url='https://ffmpeg.org/download.html'),ft.TextButton('Node.js 官方下载',url='https://nodejs.org/en/download')]),button('一键准备录制组件',self.prepare_dependencies),button('导出脱敏诊断日志',diagnostic),label('数据目录：'+str(self.home),12),label('退出软件会停止本地录制，重新打开将恢复之前启用的监控任务。',12)]
    async def prepare_dependencies(self,e=None):
        if self.installing: return False
        if binary('ffmpeg') and binary('ffprobe'): return True
        self.installing=True
        self.banner.value='首次运行：正在准备录制组件（约105MB），请保持联网，无需登录或安装软件。'
        self.page.update()
        loop=asyncio.get_running_loop()
        def show_progress(size):
            def update():
                if not self.exiting:
                    self.banner.value=f'正在准备录制组件：已下载 {size/1024**2:.0f} MB / 105 MB'
                    self.page.update()
            loop.call_soon_threadsafe(update)
        try:
            from core.dependency_setup import install_ffmpeg
            await asyncio.to_thread(install_ffmpeg,show_progress)
            self.banner.value='录制组件准备完成。可以添加本人或已获授权的直播链接。'
            return True
        except Exception:
            logging.getLogger('livewatch.app').exception('自动准备录制组件失败')
            self.banner.value='录制组件下载失败。请检查网络，在软件设置中点击“一键准备录制组件”重试。'
            return False
        finally:
            self.installing=False
            if not self.exiting: self.page.update()
    async def refresh(self):
        while not self.exiting:
            await asyncio.sleep(2)
            if self.selected in (0,2): self.render()
    async def show(self):
        self.page.window.visible=True; self.page.window.minimized=False; self.page.update(); await self.page.window.to_front()
    async def hide(self,e=None):
        self.close_dialog(); self.page.window.visible=False; self.page.update()
    async def quit(self,e=None):
        if self.exiting: return
        self.exiting=True; self.banner.value='正在安全停止录制并保存文件，请稍候……'; self.page.update()
        await self.monitor.shutdown()
        if self.tray: self.tray.stop()
        self.store.close(); await self.page.window.destroy()
    async def window_event(self,e):
        if e.type==ft.WindowEventType.MINIMIZE and self.tray:
            self.page.window.visible=False; self.page.update()
        if e.type==ft.WindowEventType.CLOSE:
            actions=[ft.TextButton('取消',on_click=self.close_dialog)]
            if self.tray: actions.append(button('继续后台录制',self.hide))
            actions.append(button('保存并退出',self.quit))
            self.page.show_dialog(ft.AlertDialog(title=label('关闭 LiveWatch'),content=label('退出会停止录制。后台运行需要电脑保持开机且不休眠。'),actions=actions))
    def start_tray(self):
        if os.name!='nt': return
        try:
            import pystray
            from PIL import Image,ImageDraw
            image=Image.new('RGB',(64,64),'white'); draw=ImageDraw.Draw(image); draw.ellipse((9,9,55,55),fill=GREEN)
            def schedule(func):
                def callback(icon,item): self.page.run_task(func)
                return callback
            self.tray=pystray.Icon('LiveWatch',image,'LiveWatch 直播观察助手',menu=pystray.Menu(
                pystray.MenuItem('打开主界面',schedule(self.show),default=True),
                pystray.MenuItem('启动全部监控',schedule(self.action(self.monitor.start_all))),
                pystray.MenuItem('停止全部监控',schedule(self.action(self.monitor.stop_all))),
                pystray.MenuItem('打开录像目录',schedule(self.action(open_path,self.root()))),
                pystray.MenuItem('退出软件',schedule(self.quit))))
            threading.Thread(target=self.tray.run,daemon=True).start()
        except Exception:
            self.tray=None; logging.getLogger('livewatch.app').exception('系统托盘启动失败')

async def main(page):
    app=Desktop(page); app.start_tray(); page.run_task(app.refresh)
    if os.environ.get('LIVEWATCH_PORTABLE') and not os.environ.get('LIVEWATCH_GUI_SMOKE'):
        await app.prepare_dependencies()
    app.monitor.resume()
    smoke=os.environ.get('LIVEWATCH_GUI_SMOKE')
    if smoke:
        for index in range(4): app.selected=index; app.render(); await asyncio.sleep(.3)
        Path(smoke).write_text('GUI mounted: all four pages rendered',encoding='utf-8')
        await app.quit()
