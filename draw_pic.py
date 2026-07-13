from manim import *
import numpy as np


class GeometryFinal(ThreeDScene):
    def construct(self):
        # =========================
        # 全局视觉参数
        # =========================
        BG_COLOR = WHITE  # 背景
        AUX_COLOR = BLACK  # 辅助线、虚线、角弧、文字
        TEXT_COLOR = BLACK  # 标签文字
        POINT_COLOR = BLACK  # 顶点/点标记（如果你也想统一成黑色）

        self.camera.background_color = BG_COLOR

        # =========================
        # 一些基础函数
        # =========================
        def unit(v):
            v = np.array(v, dtype=float)
            n = np.linalg.norm(v)
            if n < 1e-8:
                return v
            return v / n

        def proj_to_base(P):
            """投影到平面 ABCD（即 z=0）"""
            return np.array([P[0], P[1], 0.0])

        def signed_angle(u, v, normal):
            """
            在给定法向 normal 的平面中，
            计算从 u 旋到 v 的有向角（范围 -pi 到 pi）
            """
            u = unit(u)
            v = unit(v)
            normal = unit(normal)
            x = np.dot(u, v)
            y = np.dot(normal, np.cross(u, v))
            return np.arctan2(y, x)

        def make_arc(center, e1, e2, normal, radius=0.4, color=WHITE, n_components=32):
            """
            在由 e1,e2 所张成、法向为 normal 的平面里画角弧
            """
            e1 = unit(e1)
            normal = unit(normal)

            # 在该平面内，与 e1 垂直的方向
            e_perp = unit(np.cross(normal, e1))
            phi = signed_angle(e1, e2, normal)

            return ParametricFunction(
                lambda t: center + radius * (np.cos(t) * e1 + np.sin(t) * e_perp),
                t_range=[0, phi],
                color=color,
            )

        def add_point_label(
                point,
                text,
                offset=np.array([0.12, 0.12, 0.0]),
                dot_color=GRAY_B,
                scale=0.55):

            # 三维点
            dot = Dot3D(
                point=point,
                radius=0.045,
                color=dot_color
            )

            # 标签始终黑色，位置仍绑定到对应点
            label = MathTex(
                text,
                color=BLACK
            ).scale(scale)

            label.move_to(point + offset)

            return VGroup(dot, label)

        # =========================
        # 参数
        # =========================
        alpha = 20 * DEGREES    # 两平面夹角, 42
        L = 7.0                 # AB 长度
        W = 9.0                 # AD 长度,3.4
        H = 5.0                 # 倾斜方向“长度”,3.0

        # =========================
        # 平面 ABCD
        # 让 AB 沿 x 轴，ABCD 位于 z=0
        # =========================
        A = np.array([-3.5, -1.6, 0.0])
        B = np.array([ 3.5, -1.6, 0.0])
        D = np.array([-3.5,  1.8, 0.0])
        C = np.array([ 3.5,  1.8, 0.0])

        # =========================
        # 平面 ABEF
        # 与 ABCD 共边 AB，并绕 AB 抬起 alpha
        # =========================
        lift_vec = np.array([0.0, H * np.cos(alpha), H * np.sin(alpha)])
        F = A + lift_vec
        E = B + lift_vec
        """
        base_plane = Polygon(A, B, C, D, color=BLUE_C, fill_opacity=0.22, stroke_width=3)
        slope_plane = Polygon(A, B, E, F, color=GRAY_B, fill_opacity=0.28, stroke_width=3)
        """
        base_plane = Polygon(
            A, B, C, D,
            color=BLUE_C,
            fill_opacity=0.12,
            stroke_width=3
        )
        slope_plane = Polygon(
            A, B, E, F,
            color=GRAY_B,
            fill_opacity=0.45,
            stroke_width=3
        )
        # =========================
        # 在斜面 ABEF 上取一点 M 和射线 MN
        # M = A + s*(B-A) + t*(F-A)
        # =========================
        s = 0.32
        t = 0.42
        M = A + s * (B - A) + t * (F - A)

        e_ab = unit(B - A)    # 沿 AB
        e_af = unit(F - A)    # 沿 AF（斜面内）

        # 让 MN 在斜面内，且其投影与 n' 形成 >90 度
        #d = unit(0.95 * e_ab + 0.78 * e_af)
        d = unit(0.4 * e_ab + 0.5 * e_af)
        N = M + 2.5 * d #4.0

        MN = Arrow3D(start=M, end=N, color=RED, resolution=8)

        # =========================
        # 斜面法向量 n（与 MN 共顶点 M）
        # =========================
        n_dir = unit(np.cross(e_ab, e_af))   # 斜面法向
        n_length = 2.8
        n_tip = M + n_length * n_dir
        n_arrow = Arrow3D(start=M, end=n_tip, color=GREEN_C, resolution=8)

        # =========================
        # 投影：M'、N'、n'
        # =========================
        Mp = proj_to_base(M)
        Np = proj_to_base(N)

        # M'N'
        proj_ray = Arrow3D(start=Mp, end=Np, color=YELLOW_D, resolution=8)

        # n' 从 M' 出发
        n_proj_dir = unit(proj_to_base(n_dir))
        n_proj_tip = Mp + 1.7 * n_proj_dir
        n_proj_arrow = Arrow3D(start=Mp, end=n_proj_tip, color=GREEN_A, resolution=8)

        # =========================
        # 投影虚线：M->M'，N->N'，n_tip -> n_proj_tip
        # =========================
        dash_M = DashedLine(M, Mp, color=AUX_COLOR, dash_length=0.08)
        dash_N = DashedLine(N, Np, color=AUX_COLOR, dash_length=0.08)
        dash_n = DashedLine(n_tip, n_proj_tip, color=AUX_COLOR, dash_length=0.08)

        # =========================
        # 为了表示 gamma，把 MN 平移到 M'，得到 M'N''
        # =========================
        Npp = Mp + (N - M)   # 平移后的终点 N''
        translated_MN = DashedLine(Mp, Npp, color=RED_B, dash_length=0.08)

        # =========================
        # O1 取在 M'N' 上
        # =========================
        O1 = Mp + 0.60 * (Np - Mp)

        # =========================
        # 在由 M'N' 和 M'N'' 张成的平面 Π 中，
        # 过 O1 作垂直于 M'N' 的线，交 M'N'' 于 O2
        # 这对应你描述中用于后续构造的关键辅助对象
        # =========================
        p = unit(Np - Mp)     # M'N' 方向
        q = unit(Npp - Mp)    # M'N'' 方向（平移后的 MN 方向）

        # 在平面 Π 中，找一个与 p 垂直的方向 u
        u = q - np.dot(q, p) * p
        u = unit(u)

        # 解 O1 + lam*u = Mp + mu*q，求 O2
        # 即 lam*u - mu*q = Mp - O1
        A_mat = np.column_stack((u, -q))
        rhs = Mp - O1
        lam_mu = np.linalg.lstsq(A_mat, rhs, rcond=None)[0]
        lam = lam_mu[0]
        O2 = O1 + lam * u

        # =========================
        # 构造“法平面”和其与 ABCD 的交线方向
        # 这里只计算，不显示法平面本身
        # =========================
        normal_Pi = unit(np.cross(p, q))          # 平面 Π 的法向
        normal_sigma = unit(np.cross(u, normal_Pi))  # 法平面 sigma 的法向

        zhat = np.array([0.0, 0.0, 1.0])

        # sigma 与 z=0 的交线方向
        inter_dir = np.cross(normal_sigma, zhat)
        inter_dir = unit(inter_dir)

        # 为了让图更好看，选一个方向
        if np.dot(inter_dir, np.array([-0.8, -0.8, 0.0])) < 0:
            inter_dir = -inter_dir

        O3 = O1 - 2.2 * inter_dir

        # O1O2：虚线
        O1O2 = DashedLine(O1, O2, color=AUX_COLOR, dash_length=0.08)

        # O1O3：线段
        O1O3 = Line3D(start=O1, end=O3, color=BLUE_B, thickness=0.03)

        # O3O2：射线
        O3O2 = Arrow3D(start=O3, end=O2, color=TEAL_B, resolution=8)

        # =========================
        # 角 α：两平面夹角
        # 在点 A 附近，位于垂直于 AB 的截面中
        # =========================
        """
        alpha_center = A + 0.22 * (B - A)
        alpha_arc = make_arc(
            center=alpha_center,
            e1=unit(D - A),
            e2=unit(F - A),
            normal=unit(B - A),
            radius=0.48,
            color=WHITE,
        )
        """
        alpha_center = B
        alpha_arc = make_arc(
            center=B,
            e1=unit(C - B),
            e2=unit(E - B),
            normal=unit(B - A),
            radius=0.55,
            color=AUX_COLOR,
        )
        alpha_label = MathTex(r"\alpha", color=TEXT_COLOR).scale(0.65)

        # 沿 ∠CBE 的角平分方向放置 alpha，更贴近角弧
        alpha_bisector = unit(unit(C - B) + unit(E - B))
        alpha_label.move_to(
            B + 0.40 * alpha_bisector + np.array([-0.02, -0.02, 0.02])
        )

        # =========================
        # 角 β：M'N' 与 n' 的夹角
        # =========================
        beta_arc = make_arc(
            center=Mp,
            e1=unit(Np - Mp),
            e2=unit(n_proj_tip - Mp),
            normal=np.array([0.0, 0.0, 1.0]),
            radius=0.42,
            color=AUX_COLOR,
        )
        beta_label = MathTex(r"\beta", color=TEXT_COLOR).scale(0.65)

        # beta 放在两条边之间，并靠近角弧
        beta_bisector = unit(
            unit(Np - Mp) + unit(n_proj_tip - Mp)
        )
        beta_label.move_to(
            Mp + 0.35 * beta_bisector #0.35
            - 0.08 * unit(B - A)
            + np.array([0.0, -0.5, 0.02])
        )

        # =========================
        # 角 γ：M'N' 与平移后的 M'N''
        # =========================
        gamma_arc = make_arc(
            center=Mp,
            e1=unit(Np - Mp),
            e2=unit(Npp - Mp),
            normal=normal_Pi,
            radius=0.55,
            color=AUX_COLOR,
        )
        gamma_label = MathTex(r"\alpha^{\prime}", color=TEXT_COLOR).scale(0.65)
        gamma_label.move_to(Mp + np.array([0.6, 0.28, 0]))

        # =========================
        # 角 θ：∠O1O3O2
        # =========================
        theta_arc = make_arc(
            center=O3,
            e1=unit(O1 - O3),
            e2=unit(O2 - O3),
            normal=unit(np.cross(O1 - O3, O2 - O3)),
            radius=0.33,
            color=AUX_COLOR,
        )
        theta_label = MathTex(r"\alpha^{\prime\prime}", color=TEXT_COLOR).scale(0.65)

        # 沿 ∠O1O3O2 的角平分方向放置 theta，
        # 再稍微往左偏一点，避免靠近 O3 右侧
        theta_bisector = unit(unit(O1 - O3) + unit(O2 - O3))
        theta_label.move_to(
            O3 + 0.34 * theta_bisector + np.array([-0.10, 0.02, 0.02])
        )

        # =========================
        # 点和标签
        # =========================
        pts = VGroup(
            add_point_label(A, "A", np.array([-0.15, -0.12, 0.0])),
            add_point_label(B, "B", np.array([ 0.15, -0.12, 0.0])),
            add_point_label(C, "C", np.array([ 0.15,  0.12, 0.0])),
            add_point_label(D, "D", np.array([-0.15,  0.12, 0.0])),
            add_point_label(E, "E", np.array([ 0.15,  0.15, 0.08])),
            add_point_label(F, "F", np.array([-0.15,  0.15, 0.08])),

            add_point_label(M, "M", np.array([0.18, 0.12, 0.18])),
            add_point_label(N, "N", np.array([0.14, 0.08, 0.10])),

            add_point_label(
                Mp,
                "M'",
                np.array([-0.30, -0.10, 0.0])
            ),
            add_point_label(Np, "N'", np.array([0.12, -0.14, 0.0])),

            add_point_label(O1, "O_1", np.array([0.14, -0.10, 0.0])),
            add_point_label(O2, "O_2", np.array([0.15, 0.10, 0.10])),
            add_point_label(O3, "O_3", np.array([0.15, 0.10, 0.0])),
        )

        # n 与 n' 的标注
        n_label = MathTex("n", color=BLACK).scale(0.65)
        n_label.move_to(n_tip + np.array([0.10, 0.12, 0.10]))

        np_label = MathTex("n'", color=BLACK).scale(0.65)
        np_label.move_to(n_proj_tip + np.array([0.10, -0.10, 0.0]))

        # =========================
        # 以 n' 为原点建立局部坐标系
        # x轴：AB方向
        # y轴：n'M'方向
        # z轴：n'n方向
        # =========================

        ey = unit(B - A)
        ex = unit(n_proj_tip - Mp)
        ez = unit(n_tip - n_proj_tip)

        axis_length_x = 2.4
        axis_length_y = 2.5
        axis_length_z = 4.1

        x_axis = Arrow3D(
            start=n_proj_tip,
            end=n_proj_tip + axis_length_x * ex,
            color=RED,
            resolution=8
        )

        y_axis = Arrow3D(
            start=n_proj_tip,
            end=n_proj_tip + axis_length_y * ey,
            color=GREEN,
            resolution=8
        )

        z_axis = Arrow3D(
            start=n_proj_tip,
            end=n_proj_tip + axis_length_z * ez,
            color=BLUE,
            resolution=8
        )

        x_label = MathTex("x", color=BLACK).scale(0.55)
        y_label = MathTex("y", color=BLACK).scale(0.55)
        z_label = MathTex("z", color=BLACK).scale(0.55)

        x_label.move_to(n_proj_tip + 1.05 * axis_length_x * ex)
        y_label.move_to(n_proj_tip + 1.05 * axis_length_y * ey)
        z_label.move_to(n_proj_tip + 1.02 * axis_length_z * ez)


        Npp_label = MathTex("N''", color=BLACK).scale(0.6)
        Npp_label.move_to(Npp + np.array([0.10, 0.08, 0.10]))

        # =========================
        # 白色背景
        # =========================

        self.camera.background_color = WHITE

        # =========================
        # 将模型整体居中
        # =========================

        # 几何对象
        geom_group = VGroup(
            base_plane,
            slope_plane,

            MN,
            n_arrow,

            proj_ray,
            n_proj_arrow,

            dash_M,
            dash_N,
            dash_n,

            translated_MN,

            x_axis,
            y_axis,
            z_axis,

            O1O2,
            O1O3,
            O3O2,

            alpha_arc,
            beta_arc,
            gamma_arc,
            theta_arc,
        )

        # 文字对象
        text_group = VGroup(
            pts,

            alpha_label,
            beta_label,
            gamma_label,
            theta_label,

            n_label,
            np_label,
            Npp_label,
        )

        # 总对象
        full_group = VGroup(
            geom_group,
            text_group,
        )

        # 不整体平移对象：
# ThreeDScene中的文字需要保持在原始三维坐标附近，
# 否则固定朝向文字会与对应点分离。
# 如需调整构图，使用camera frame_center/zoom调整。

        # =========================
        # 相机
        # =========================
        self.camera.frame_center = np.array([0, 0, 1.2])

        self.set_camera_orientation(
            phi=70 * DEGREES,
            theta=-66 * DEGREES,
            zoom=1.28,
        )

        # =========================
        # 添加三维对象
        # =========================

        self.add(
            base_plane,
            slope_plane,

            MN,
            n_arrow,

            proj_ray,
            n_proj_arrow,

            dash_M,
            dash_N,
            dash_n,

            translated_MN,

            x_axis,
            y_axis,
            z_axis,

            O1O2,
            O1O3,
            O3O2,

            alpha_arc,
            beta_arc,
            gamma_arc,
            theta_arc,
        )

        # =========================
        # 添加始终面向摄像机的文字
        # =========================

        # 每一个文字对象单独固定朝向摄像机
        # 避免VGroup嵌套导致标签位置异常
        text_objects = [
            alpha_label,
            beta_label,
            gamma_label,
            theta_label,
            n_label,
            np_label,
            Npp_label,
            x_label,
            y_label,
            z_label,
        ]

        # pts 中包含点和对应文字，拆开处理
        for item in pts:
            dot = item[0]
            label = item[1]
            self.add_fixed_orientation_mobjects(label)
            self.add(dot)

        for obj in text_objects:
            self.add_fixed_orientation_mobjects(obj)

        # 保持初始视角
        self.wait(1)

        """
        # 摄像机绕Z轴旋转一圈
        self.move_camera(
            theta=-52 * DEGREES + 360 * DEGREES,
            run_time=8
        )

        self.wait(2)
        """