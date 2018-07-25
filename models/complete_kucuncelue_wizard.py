# -*- coding: utf-8 -*-
from odoo import api, models, fields, tools
from odoo.exceptions import ValidationError
import traceback

# import logging
# _logger = logging.getLogger(__name__)

class BaojingWizard(models.TransientModel):
    _name = "wms.wizard.completekucuncelue"
    _description = "备件库存策略向导"

    name = fields.Char(default="库存报警设置")
    state = fields.Selection([
        ('selcangku', '选仓库'),
        ('selbeijianext', '选备件'),
        ], default='selcangku')

    cangku = fields.Many2one('wms.cangku', '选择要设置的仓库')
    shebei = fields.Many2one('wms.shebei', '备件所属设备')
    beijian = fields.Many2one('wms.beijian', '备件名称')
    beijianext = fields.Many2one('wms.beijianext', '备件型号')

    @api.depends('beijianext.image')
    def _compute_img(self):
        for i in self:
            i.image = i.beijianext.image

    rukushuliang = fields.Integer('入库数量')
    huowei = fields.Many2one('wms.huowei', '货位')
    changjia = fields.Many2one('wms.changjia', '厂家')
    shengchanriqi = fields.Date('生产日期', default=fields.Date.today)
    pihao = fields.Char("批次号")
    image = fields.Binary("图片", compute='_compute_img')

    tbeijians = fields.Many2many('wms.beijian')
    tbeijianexts = fields.Many2many('wms.beijianext')
    info = fields.Char()

    @api.onchange('shebei')
    def onchange_shebei(self):
        self.tbeijians = self.shebei.beijians
        self.tbeijianexts = self.shebei.beijianexts
        self.beijian = False

    @api.onchange('beijian')
    def onchange_beijian(self):
        self.beijianext = False

    @api.onchange('beijianext')
    def onchange_beijianext(self):
        self.huowei = False

    @api.onchange('cangku')
    def onchange_cangku(self):
        self.huowei = False

    # @api.onchange('rukushuliang')
    # def onchange_rukushuliang(self):

    #     if self.rukushuliang > 1:
    #         self.showwarn = True
    #     else:
    #         self.showwarn = False

    def check_missing_settings(self):
        # 查找匹配货位
        caller = traceback.extract_stack()[-2][2]
        if self.env['wms.huowei'].search_count([
            ('beijianext', '=', self.beijianext.id),
            ('cangku', '=', self.cangku.id)]) == 0:
            return {
                'name': '为此备件分配货位',
                'type': 'ir.actions.act_window',
                'res_model': 'wms.wizard.newhuowei',
                'views': [[self.env.ref('wms.newhuowei_wizard_view').id, 'form']],
                'target': 'new_no_close' if caller == 'progress_next' else 'new',
                'context': {
                    'cangku': self.cangku.id,
                    'beijianext': self.beijianext.id,
                    'wizard': self.id,}}
        elif not self.huowei:
            # 找到匹配货位后自动填写最新增加的货位
            self.huowei = self.env['wms.huowei'].search([
                ('beijianext', '=', self.beijianext.id),
                ('cangku', '=', self.cangku.id)],
                order='create_date desc', limit=1)
        if self.env['wms.kucuncelue'].search_count([
            ('beijianext', '=', self.beijianext.id),
            ('cangku', '=', self.cangku.id)]) == 0:
            return {
                'name': '为此备件设置库存报警',
                'type': 'ir.actions.act_window',
                'res_model': 'wms.wizard.setkucuncelue',
                'views': [[
                    self.env.ref('wms.setkucuncelue_wizard_view').id, 'form']],
                'target': 'new_no_close' if caller == 'progress_next' else 'new',
                'context': {
                    'cangku': self.cangku.id,
                    'beijianext': self.beijianext.id,
                    'wizard': self.id,}}
        self.state = 'fillform'
        return {'type': "ir_actions_act_window_donothing",} \
            if caller == 'progress_next' else \
                {'type': 'ir_actions_act_window_close',}

    @api.multi
    def progress_next(self):
        self.ensure_one()
        if self.state == 'selcangku':
            if not self.cangku:
                raise ValidationError("请选择仓库！")
            self.state = 'selbeijianext'
        elif self.state == 'selbeijianext':
            if not self.shebei:
                raise ValidationError("请选择设备！")
            if not self.beijian:
                raise ValidationError("请选择备件！")
            if not self.beijianext:
                raise ValidationError("请选择备件型号！")
            self.info = '将%s（%s）入库到%s' % (self.beijian.name, self.beijianext.name, self.cangku.name)
            return self.check_missing_settings()
        elif self.state == 'fillform':
            if not self.rukushuliang or self.rukushuliang < 1:
                raise ValidationError("入库数量不能小于 1！")
            if not self.huowei:
                raise ValidationError("请填写货位！")
            if not self.shengchanriqi:
                raise ValidationError("请填写生产日期！")
            self.env['wms.geti'].create({
                'xuliehao': self.env['ir.sequence'].next_by_code('wms.geti'),
                'beijianext': self.beijianext.id,
                'huowei': self.huowei.id,
                'changjia': self.changjia.id if self.changjia else False,
                'shengchanriqi': self.shengchanriqi,
                'pihao': self.pihao,
                'zhuangtai': 'zaiku',
                })
            self.state = 'confirm'
        elif self.state == 'confirm':
            pass
        return {'type': "ir_actions_act_window_donothing",}

    @api.multi
    def progress_prev(self):
        self.ensure_one()
        if self.state == 'selbeijianext':
            self.state = 'selcangku'
        elif self.state == 'fillform':
            self.state = 'selbeijianext'
        elif self.state == 'confirm':
            self.state = 'fillform'
        return {'type': "ir_actions_act_window_donothing",}

    @api.model
    def default_get(self, fields):
        res = super(RukuWizard, self).default_get(fields)
        if self.env['wms.cangku'].search_count([]) == 1:
            res['cangku'] = self.env['wms.cangku'].search([], limit=1).id
            res['state'] = 'selbeijianext'
        # res['rukushuliang'] = 1
        # res['showwarn'] = False
        return res

    def newhuowei_wizard_act_window(self):
        return {
            'name': '为此备件分配货位',
            'type': 'ir.actions.act_window',
            'res_model': 'wms.wizard.newhuowei',
            'views': [[self.env.ref('wms.newhuowei_wizard_view').id, 'form']],
            'target': 'new_no_close',
            'context': {
                'cangku': self.cangku.id,
                'beijianext': self.beijianext.id,
                'wizard': self.id,}}
