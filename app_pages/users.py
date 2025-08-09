import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode


def render(db):
    st.header("Kelola User")

    users_df = db.get_users()
    tab_list, tab_add = st.tabs(["Daftar User", "Tambah User"])

    with tab_list:
        st.subheader("Daftar User")
        if users_df.empty:
            st.info("Belum ada user selain admin.")
        else:
            display_df = users_df.copy()
            display_df = display_df[["id", "username", "role", "created_at"]]

            gb = GridOptionsBuilder.from_dataframe(display_df)
            gb.configure_default_column(resizable=True, filter=True, sortable=True)
            gb.configure_selection("single")
            gb.configure_grid_options(domLayout="autoHeight", pagination=True, paginationPageSize=10)
            grid_options = gb.build()

            grid_response = AgGrid(
                display_df,
                gridOptions=grid_options,
                data_return_mode=DataReturnMode.AS_INPUT,
                update_mode=GridUpdateMode.SELECTION_CHANGED,
                fit_columns_on_grid_load=True,
                theme="streamlit",
                height=400,
                allow_unsafe_jscode=True,
            )

            selected = grid_response.get("selected_rows", [])
            if selected:
                sel = selected[0]
                st.markdown("---")
                st.subheader(f"Edit User: {sel['username']}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    new_role = st.selectbox(
                        "Ubah Role",
                        options=["admin", "staff", "viewer"],
                        index=["admin", "staff", "viewer"].index(sel["role"]),
                        key=f"role_{sel['id']}"
                    )
                    if st.button("Simpan Role", key=f"save_role_{sel['id']}"):
                        if db.update_user_role(sel["id"], new_role):
                            st.success("Role berhasil diperbarui.")
                            st.rerun()
                        else:
                            st.error("Gagal memperbarui role.")
                with col2:
                    st.write("Reset Password")
                    pwd1 = st.text_input("Password Baru", type="password", key=f"pwd1_{sel['id']}")
                    pwd2 = st.text_input("Ulangi Password", type="password", key=f"pwd2_{sel['id']}")
                    if st.button("Simpan Password", key=f"save_pwd_{sel['id']}"):
                        if not pwd1 or pwd1 != pwd2:
                            st.warning("Password tidak cocok.")
                        else:
                            if db.update_user_password(sel["id"], pwd1):
                                st.success("Password berhasil diubah.")
                                st.rerun()
                            else:
                                st.error("Gagal mengubah password.")
                with col3:
                    st.write("Hapus User")
                    if sel["username"] == "admin":
                        st.info("User 'admin' tidak dapat dihapus.")
                    else:
                        if st.button("Hapus User", type="secondary", key=f"del_{sel['id']}"):
                            if db.delete_user(sel["id"]):
                                st.success("User dihapus.")
                                st.rerun()
                            else:
                                st.error("Gagal menghapus user.")

    with tab_add:
        st.subheader("Tambah User Baru")
        with st.form("add_user_form"):
            username = st.text_input("Username *")
            password = st.text_input("Password *", type="password")
            password2 = st.text_input("Ulangi Password *", type="password")
            role = st.selectbox("Role *", ["admin", "staff", "viewer"], index=1)
            submitted = st.form_submit_button("Tambah User")
            if submitted:
                if not username or not password or not password2:
                    st.warning("Lengkapi semua field wajib.")
                elif password != password2:
                    st.warning("Password tidak cocok.")
                else:
                    ok, msg = db.add_user(username, password, role)
                    if ok:
                        st.success("User berhasil ditambahkan.")
                        st.rerun()
                    else:
                        st.error(f"Gagal menambahkan user: {msg}")
