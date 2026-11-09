# -*- coding: utf-8 -*-
"""路由层：每个函数对应一个页面或一次表单提交。

看代码的顺序建议：
    1. /login 登录
    2. / 竞赛列表
    3. /competition/<id> 详情、/competition/<id>/signup 报名
    4. /my 待办 / 我的报名
    5. /awards 获奖、/stats 统计
"""
import datetime
import os
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash

import db

app = Flask(__name__)
# 生产环境要把这个密钥换成随机值，并且不要写进代码仓库
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret-key-please-change")

COMP_STATUS = {1: "报名中", 2: "报名截止", 3: "评审中", 4: "已公示"}
REG_STATUS = {0: "待审核", 1: "通过", 2: "驳回"}
ROLE_NAME = {0: "学生", 1: "教师", 2: "管理员"}


@app.context_processor
def inject_constants():
    """让所有模板都能直接用这几个字典，不用每个路由都传一遍。"""
    return dict(COMP_STATUS=COMP_STATUS, REG_STATUS=REG_STATUS, ROLE_NAME=ROLE_NAME)


def login_required(*roles):
    """登录校验装饰器。@login_required() 只要登录；@login_required(2) 还要求是管理员。"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "uid" not in session:
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------- 登录
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.get_user_by_username(username)
        # check_password_hash 把用户输入的密码和库里存的哈希做比对，库里的哈希无法反推出密码
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["uid"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["real_name"]
            return redirect(url_for("index"))
        flash("用户名或密码错误", "error")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------- 竞赛列表
@app.get("/")
def index():
    status = request.args.get("status", type=int)
    level = request.args.get("level", "")
    page = request.args.get("page", 1, type=int) or 1
    page = max(page, 1)
    size = 8
    comps, total = db.list_competitions(status, level, page, size)
    pages = (total + size - 1) // size
    return render_template(
        "competitions.html",
        comps=comps, total=total, page=page, pages=pages,
        status=status, level=level,
    )


# ---------------------------------------------------------------- 竞赛详情与报名
@app.get("/competition/<int:cid>")
def competition_detail(cid):
    comp = db.get_competition(cid)
    if comp is None:
        abort(404)
    regs = []
    my_reg = None
    if session.get("role") in (1, 2):          # 教师/管理员看得到报名名单
        regs = db.list_registrations(cid)
    elif session.get("role") == 0:             # 学生看自己的报名状态
        my_reg = db.get_my_registration(cid, session["uid"])
    return render_template("competition_detail.html", comp=comp, regs=regs, my_reg=my_reg)


@app.post("/competition/<int:cid>/signup")
@login_required(0)
def signup(cid):
    comp = db.get_competition(cid)
    if comp is None:
        abort(404)
    if comp["status"] != 1:
        flash("该竞赛当前不在报名阶段", "error")
        return redirect(url_for("competition_detail", cid=cid))
    if comp["sign_end"] < datetime.date.today().isoformat():
        flash("报名已截止", "error")
        return redirect(url_for("competition_detail", cid=cid))

    ok, message = db.sign_up(cid, session["uid"])
    flash(message, "ok" if ok else "error")
    return redirect(url_for("competition_detail", cid=cid))


# ---------------------------------------------------------------- 发布竞赛（管理员）
@app.route("/competition/new", methods=["GET", "POST"])
@login_required(2)
def new_competition():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        sign_start = request.form.get("sign_start", "")
        sign_end = request.form.get("sign_end", "")
        if not title or not sign_start or not sign_end:
            flash("竞赛名称和报名起止日期不能为空", "error")
            return render_template("competition_form.html")
        if sign_end < sign_start:
            flash("报名截止日期不能早于开始日期", "error")
            return render_template("competition_form.html")

        db.create_competition({
            "title": title,
            "level": request.form.get("level", "校级"),
            "category": request.form.get("category", "").strip(),
            "organizer": request.form.get("organizer", "").strip(),
            "sign_start": sign_start,
            "sign_end": sign_end,
            "contest_date": request.form.get("contest_date", ""),
            "status": request.form.get("status", 1, type=int) or 1,
            "description": request.form.get("description", "").strip(),
            "create_by": session["uid"],
        })
        flash("竞赛已发布", "ok")
        return redirect(url_for("index"))
    return render_template("competition_form.html")


# ---------------------------------------------------------------- 审核与打分
@app.post("/registration/<int:rid>/audit")
@login_required(1, 2)
def audit(rid):
    action = request.form.get("action")
    if action not in ("pass", "reject"):
        flash("参数错误", "error")
        return redirect(request.referrer or url_for("my"))
    status = 1 if action == "pass" else 2
    db.audit(rid, status, request.form.get("reason", "").strip())
    flash("审核完成", "ok")
    return redirect(request.referrer or url_for("my"))


@app.post("/registration/<int:rid>/score")
@login_required(1)
def save_score(rid):
    raw = request.form.get("score", "").strip()
    try:
        value = float(raw)
    except ValueError:
        flash("成绩必须是数字", "error")
        return redirect(url_for("my"))
    if not 0 <= value <= 100:
        flash("成绩必须在 0 到 100 之间", "error")
        return redirect(url_for("my"))
    ok, message = db.save_score(rid, session["uid"], value,
                                request.form.get("comment", "").strip())
    flash(message, "ok" if ok else "error")
    return redirect(url_for("my"))


@app.post("/registration/<int:rid>/score/delete")
@login_required(1, 2)
def delete_score(rid):
    """撤销成绩：撤销后这条报名回到「待打分」，可以重新打分。"""
    ok, message = db.delete_score(rid)
    flash(message, "ok" if ok else "error")
    return redirect(request.referrer or url_for("my"))


# ---------------------------------------------------------------- 待办 / 我的报名
@app.get("/my")
@login_required()
def my():
    if session["role"] == 0:
        return render_template("my.html", regs=db.list_my_registrations(session["uid"]))
    return render_template(
        "my.html",
        pending=db.list_pending(),
        ungraded=db.list_ungraded(),
        scored=db.list_scored_registrations(),
    )


# ---------------------------------------------------------------- 获奖公示
@app.get("/awards")
def awards():
    return render_template(
        "awards.html",
        awards=db.list_awards(),
        scored=db.list_scored() if session.get("role") == 2 else [],
    )


@app.post("/awards/<int:rid>/publish")
@login_required(2)
def publish_award(rid):
    level = request.form.get("level", "").strip()
    if level not in ("一等奖", "二等奖", "三等奖"):
        flash("奖项等级不正确", "error")
    else:
        db.publish_award(rid, level)
        flash("获奖信息已公示", "ok")
    return redirect(url_for("awards"))


@app.post("/awards/<int:rid>/revoke")
@login_required(2)
def revoke_award(rid):
    """撤销获奖公示，撤销后该成绩解锁。"""
    db.revoke_award(rid)
    flash("获奖公示已撤销，该成绩可以重新修改", "ok")
    return redirect(url_for("awards"))


# ---------------------------------------------------------------- 公告
@app.route("/notices", methods=["GET", "POST"])
def notices():
    if request.method == "POST":
        if session.get("role") != 2:
            abort(403)
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("标题和内容不能为空", "error")
        else:
            db.add_notice(title, content, session["uid"])
            flash("公告已发布", "ok")
        return redirect(url_for("notices"))
    return render_template("notices.html", notices=db.list_notices())


# ---------------------------------------------------------------- 统计
@app.get("/stats")
@login_required(1, 2)
def stats():
    return render_template(
        "stats.html",
        by_college=db.stats_by_college(),
        by_award=db.stats_by_award(),
        by_status=db.stats_by_status(),
        status_names=COMP_STATUS,
    )


# ---------------------------------------------------------------- 启动
def bootstrap():
    """第一次运行时建库并灌演示数据。"""
    if not os.path.exists(db.DB_PATH):
        db.init_db()
        db.seed_data()


if __name__ == "__main__":
    bootstrap()
    app.run(host="127.0.0.1", port=5000, debug=True)
