import pytest
from types import SimpleNamespace
from ui.desktop import Desktop

class Page:
    def __init__(self): self.window=SimpleNamespace(); self.controls=[]; self.dialog=None
    def add(self,*controls): self.controls.extend(controls)
    def update(self): pass
    def show_dialog(self,dialog): self.dialog=dialog
    def pop_dialog(self): self.dialog=None

@pytest.mark.asyncio
async def test_four_pages_and_dialogs(tmp_path):
    page=Page(); app=Desktop(page,tmp_path)
    i=app.store.add('https://live.douyin.com/123',name='测试主播')
    for index, title in enumerate(('直播监控', '录像管理', '数据统计', '软件设置')):
        await app.nav.controls[index].on_click(None)
        assert app.selected == index
        heading = app.body.controls[0]
        if index == 0:
            heading = heading.controls[0]
        assert heading.controls[0].value == title
        assert sum(bool(item.style.bgcolor) for item in app.nav.controls) == 1
        assert app.nav.controls[index].style.bgcolor is not None
    app.add_dialog(); assert page.dialog is not None
    app.edit(app.store.task(i)); assert page.dialog is not None
    app.delete_task(app.store.task(i)); assert page.dialog is not None
    app.store.close()
