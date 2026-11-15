from types import SimpleNamespace
from ui.desktop import Desktop

class Page:
    def __init__(self): self.window=SimpleNamespace(); self.controls=[]; self.dialog=None
    def add(self,*controls): self.controls.extend(controls)
    def update(self): pass
    def show_dialog(self,dialog): self.dialog=dialog
    def pop_dialog(self): self.dialog=None

def test_four_pages_and_dialogs(tmp_path):
    page=Page(); app=Desktop(page,tmp_path)
    i=app.store.add('https://live.douyin.com/123',name='测试主播')
    for n in range(4): app.selected=n; app.render(); assert app.body.controls
    app.add_dialog(); assert page.dialog is not None
    app.edit(app.store.task(i)); assert page.dialog is not None
    app.delete_task(app.store.task(i)); assert page.dialog is not None
    app.store.close()
