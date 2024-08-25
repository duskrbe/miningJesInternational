import streamlit as st
from streamlit import session_state
from library import MiningData as md
import pandas as pd

st.set_page_config(
    page_title="Sistem Data Mining Cv Jes International",
    page_icon=":building_construction:",
)


class UserInterface:
    # Halaman upload transaksi
    def halamanUploadTransaksi():
        # Header Section
        st.title("Sistem Data Mining Rekomendasi Produk")
        st.markdown(
            "Sistem data mining untuk penempatan tata letak produk di CV. Jes International berdasarkan pola barang yang dipesan customer"
        )
        st.divider()

        upload = md.uploadTransaksi()
        md.validasiUploadTransaksi(upload)

        if st.button(
            "Proses Aturan Asosiasi", type="primary", use_container_width=True
        ):
            if "upload_transaksi" in session_state:
                if not md.getUploadTransaksi().empty:
                    session_state.selected_page = "Proses Aturan Asosiasi"
                    st.experimental_rerun()
                else:
                    st.error(
                        "Belum ada file transaksi yang diunggah. Silahkan upload terlebih dahulu!"
                    )

    # Halaman proses aturan asosiasi
    def halamanProsesAturanAsosiasi():
        st.markdown("<h1>Halaman Proses Aturan Asosiasi</h1>", unsafe_allow_html=True)
        st.divider()
        if not md.getUploadTransaksi().empty:
            if "proses_aturan_asosiasi" not in session_state:
                session_state.proses_aturan_asosiasi = False
            transaksi = md.getUploadTransaksi()
            pilihAtribut = md.pilihAtribut(transaksi)
            cleaningData = md.cleaningData(pilihAtribut)
            list_transaksi, transformData = md.transformData(cleaningData)
            list_produk = md.buatListProduk(cleaningData)
            minSupport = md.minSupport(list_produk, list_transaksi)
            md.rules(transformData, minSupport)
            md.tampilProsesAturanAsosiasi()
            session_state.proses_aturan_asosiasi = True
            if st.button(
                "Lihat Hasil Rekomendasi",
                use_container_width=True,
                type="primary",
            ):
                session_state.selected_page = "Hasil Rekomendasi"
                st.experimental_rerun()
        else:
            st.error(
                "Belum ada file transaksi yang diunggah. Silahkan upload terlebih dahulu!"
            )
            if st.button("Upload File", type="primary", use_container_width=True):
                session_state.selected_page = "Upload File Transaksi"
                st.experimental_rerun()

    # Halaman hasil rekomendasi
    def halamanHasilRekomendasi():
        st.markdown("<h1>Halaman Hasil Rekomendasi</h1>", unsafe_allow_html=True)
        st.divider()
        session_state.proses_aturan_asosiasi = True
        if md.periksaUploadTransaksi():
            df_association_unique = session_state.df_association_unique
            if df_association_unique.empty:
                st.error(
                    "Tidak ada rekomendasi karena tidak terdapat rule yang dihasilkan"
                )
            else:
                # membuat dataframe rekomendasi
                nama_barang = []
                kode_rules = []

                for idx, row in df_association_unique.iterrows():
                    for barang in row["Rules"]:
                        nama_barang.append(barang)
                        kode_rules.append(idx + 1)

                list_rules_produk = pd.DataFrame(
                    {"Rekomendasi": nama_barang, "Kode Rules": kode_rules}
                )
                # Menggabungkan nilai Rekomendasi dengan Kode_Rules yang sama
                df_rekomendasi = (
                    list_rules_produk.groupby("Kode Rules")
                    .agg(
                        {
                            "Rekomendasi": lambda x: (
                                (
                                    f"Barang ({x.iloc[0]}) lebih condong ditempatkan berdekatan dengan ({x.iloc[1]})"
                                    + (
                                        f",({','.join(x.iloc[2:])})"
                                        if len(x) > 2
                                        else ""
                                    )
                                    + " karena sering dipesan bersamaan."
                                )
                                if len(x) > 1
                                else f"({x.iloc[0]})"
                                + " karena sering dipesan bersamaan."
                            )
                        }
                    )
                    .reset_index()
                )

                df_rekomendasi["Kode Rules"] = df_rekomendasi.reset_index().index + 1
                df_rekomendasi["Rekomendasi"] = (
                    df_rekomendasi["Rekomendasi"].str.split(",").astype(str)
                )
                df_rekomendasi["Rekomendasi"] = (
                    df_rekomendasi["Rekomendasi"]
                    .str.replace("[", "")
                    .str.replace("]", "")
                    .str.replace("'", "")
                )

                df_dict = dict(tuple(df_rekomendasi.groupby("Kode Rules")))

                # st.markdown("<h4>Rekomendasi</h4>", unsafe_allow_html=True)
                st.markdown(
                    "<h5>INFORMASI :</h5>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<p>Hasil rekomendasi ini adalah representasi pengetahuan yang dapat digunakan sebagai referensi bagi petugas CV. Jes International untuk membantu dalam penempatan barang yang dapat diletakkan berdekatan atau bersamaan sesuai pola pesanan customer. </p>",
                    unsafe_allow_html=True,
                )
                st.write(
                    "Diketahui terdapat ",
                    len(df_dict),
                    " rekomendasi",
                )
                md.unduhRekomendasi(df_rekomendasi)
                st.divider()
                md.tampilHasilRekomendasi(df_dict)
        else:
            st.error(
                "Belum ada file transaksi yang diunggah. Silahkan upload terlebih dahulu!"
            )
            if st.button("Upload File", type="primary", use_container_width=True):
                session_state.selected_page = "Upload File Transaksi"
                st.experimental_rerun()


# Main function to run the app
class Main:
    def main():
        if "selected_page" not in session_state:
            session_state.selected_page = "Upload File Transaksi"

        st.sidebar.title("Menu Navigasi")
        ui = UserInterface
        pages = {
            "Upload File Transaksi": ui.halamanUploadTransaksi,
            "Proses Aturan Asosiasi": ui.halamanProsesAturanAsosiasi,
            "Hasil Rekomendasi": ui.halamanHasilRekomendasi,
        }

        # Display buttons for each page in the sidebar
        selected_page = st.sidebar.button(
            "Upload File Transaksi", use_container_width=True
        )
        if selected_page:
            session_state.selected_page = "Upload File Transaksi"

        selected_page = st.sidebar.button(
            "Proses Aturan Asosiasi", use_container_width=True
        )
        if selected_page:
            session_state.selected_page = "Proses Aturan Asosiasi"

        selected_page = st.sidebar.button("Hasil Rekomendasi", use_container_width=True)
        if selected_page:
            session_state.selected_page = "Hasil Rekomendasi"

        # Execute the selected page function
        pages[session_state.selected_page]()


if __name__ == "__main__":
    # # Create an instance of Main class
    # main_app = Main()
    # # Call main method using the instance
    # main_app.main()
    Main.main()
