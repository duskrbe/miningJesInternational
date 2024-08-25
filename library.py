import streamlit as st
from streamlit import session_state
import pandas as pd
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import association_rules, fpgrowth
from io import BytesIO


class MiningData:
    def periksaUploadTransaksi():
        # Initialize the session_state dictionary if it doesn't exist
        if "upload_transaksi" not in st.session_state:
            session_state.upload_transaksi = None
        if "df_transaksi" not in st.session_state:
            session_state.df_transaksi = pd.DataFrame()
        # Memeriksa apakah 'upload_transaksi' tidak kosong dan DataFrame 'df_transaksi' tidak kosong
        return (
            session_state.get("upload_transaksi") is not None
            and not session_state.df_transaksi.empty
        )

    def setUploadTransaksi(newUploadTransaksi, newDFTransaksi):
        session_state.upload_transaksi = newUploadTransaksi
        session_state.df_transaksi = newDFTransaksi

    def getUploadTransaksi():
        if MiningData.periksaUploadTransaksi():
            return session_state.df_transaksi
        return pd.DataFrame()

    # def periksaListProduk():
    #     return session_state.get("list_produk") is not None

    def getListProduk():
        if session_state.get("list_produk") is not None:
            return session_state.list_produk
        return pd.DataFrame()

    def uploadTransaksi():
        if MiningData.getUploadTransaksi().empty:
            # File uploader
            st.markdown(
                "<h4>Upload file transaksi penjualan</h4>",
                unsafe_allow_html=True,
            )
            upload = st.file_uploader(
                "Pilih File Data Transaksi Dengan Format Excel file (.xlsx)",
                type="xlsx",
            )
            return upload
        else:
            st.success("Berhasil mengupload file transaksi")
            if st.button("Ganti data file transaksi"):
                MiningData.setUploadTransaksi(None, None)
                session_state.df_association_unique = pd.DataFrame()
                session_state.cek_proses_asosiasi = False
                st.rerun()

    def validasiUploadTransaksi(file):
        if file:
            dataframe_transaction = pd.read_excel(file)
            # Mengecek apakah kolom yang dibutuhkan ada di DataFrame
            required_columns = ["NO INVOICE", "KODE"]
            missing_columns = [
                col
                for col in required_columns
                if col not in dataframe_transaction.columns
            ]
            if len(missing_columns) == 0:
                MiningData.setUploadTransaksi(file, dataframe_transaction)
                st.rerun()
            else:
                st.error("Pastikan file transaksi sesuai dengan format")

    def pilihAtribut(transaksi):
        # Ambil atribut tertentu
        pilihAtribut = transaksi.copy()
        pilihAtribut = pilihAtribut[["NO INVOICE", "KODE"]]
        return pilihAtribut

    def cleaningData(pilihAtribut):
        cleaningData = pilihAtribut[["NO INVOICE", "KODE"]].copy()
        # Menghapus baris yang memiliki nilai kosong di kolom 'KODE'
        cleaningData = cleaningData.dropna(subset=["NO INVOICE", "KODE"])
        return cleaningData

    def transformData(cleaningData):
        # Get all the transactions as a list of lists
        list_transaksi = (
            cleaningData.groupby("NO INVOICE")["KODE"]
            .apply(lambda x: list(set(x)))
            .tolist()
        )

        # The following instructions transform the dataset into the required format
        trans_encoder = TransactionEncoder()
        transformData = trans_encoder.fit(list_transaksi).transform(list_transaksi)
        transformData = pd.DataFrame(transformData, columns=trans_encoder.columns_)

        return list_transaksi, transformData

    def buatListProduk(cleaningData):
        if "list_produk" not in session_state:
            session_state.list_produk = None
        # Membuat tabel baru 'list_produk' dengan kolom 'KODE'
        list_produk = cleaningData.copy()
        list_produk = list_produk[["KODE"]]
        # Menghapus data duplikat pada nilai 'KODE'
        list_produk = list_produk.drop_duplicates(subset=["KODE"])

        # Menghitung kemunculan setiap nilai pada KODE dari tabel produk pada transaksi
        list_produk["Support"] = (
            list_produk["KODE"]
            .map(cleaningData["KODE"].value_counts())
            .fillna(0)
            .astype(int)
        )

        # Mengurutkan Support dari terbesar ke terkecil
        list_produk = list_produk.sort_values(by="Support", ascending=False)
        list_produk.reset_index(drop=True, inplace=True)
        # Mereset index dan mengatur index mulai dari 1
        list_produk.index = list_produk.index + 1

        session_state.list_produk = list_produk
        return list_produk

    def minSupport(list_produk, list_transaksi):
        get_frekuensi = list_produk["Support"].mean()
        get_len_transaksi = len(list_transaksi)
        min_support = get_frekuensi / get_len_transaksi
        min_support = round(get_frekuensi / len(list_transaksi), 2)
        return min_support

    def rules(transformData, min_support):
        min_confidence = 0.70
        if "rules" not in session_state:
            session_state.rules = None

        if "frequent_itemsets" not in session_state:
            session_state.frequent_itemsets = pd.DataFrame()

        if "df_association" not in session_state:
            session_state.df_association = pd.DataFrame()

        if "df_association_unique" not in session_state:
            session_state.df_association_unique = pd.DataFrame()

        # if "df_association_max_combination" not in session_state:
        #     session_state.df_association_max_combination = pd.DataFrame()

        # Membuat frequent itemsets
        frequent_itemsets = fpgrowth(
            transformData, min_support=min_support, use_colnames=True
        )
        session_state.frequent_itemsets = frequent_itemsets

        # Memanggil transaksi yang telah diupload untuk digunakan dalam mengubah kolom kode menjadi nama
        df_transaksi = MiningData.getUploadTransaksi()

        kode_to_nama = dict(zip(df_transaksi["KODE"], df_transaksi["NAMA BARANG"]))

        rules = association_rules(
            frequent_itemsets, metric="confidence", min_threshold=min_confidence
        )
        rules["Count items"] = rules["antecedents"].apply(lambda x: len(x)) + rules[
            "consequents"
        ].apply(lambda x: len(x))
        rules["id_rule"] = rules.reset_index().index + 1

        # Mereset index dan mengatur index mulai dari 1
        rules.reset_index(drop=True, inplace=True)
        rules.index = rules.index + 1

        session_state.rules = rules

        # Membuat dataframe dari data association rule
        df_association = rules.copy()
        # Combine antecedents and consequents into a new column 'rules' using list comprehension
        df_association["Rules"] = [
            sorted(list(row["antecedents"]) + list(row["consequents"]))
            for _, row in df_association.iterrows()
        ]

        # Simpan kolom 'confidence' dan 'lift'
        ansu = df_association["antecedent support"]
        cosu = df_association["consequent support"]
        support = df_association["support"]
        confidence = df_association["confidence"]
        lift = df_association["lift"]

        # Hapus kolom  dari dataframe
        df_association = df_association.drop(
            columns=[
                "antecedent support",
                "consequent support",
                "support",
                "confidence",
                "lift",
            ]
        )

        # Tambahkan kembali kolom 'confidence' dan 'lift' ke dataframe di akhir
        df_association["antecedent support"] = ansu
        df_association["consequent support"] = cosu
        df_association["support"] = support
        df_association["confidence"] = confidence
        df_association["lift"] = lift

        df_association.drop(
            columns=[
                "id_rule",
                "antecedents",
                "consequents",
                "leverage",
                "conviction",
                "zhangs_metric",
                "Count items",
            ],
            inplace=True,
        )

        # Mereset index dan mengatur index mulai dari 1
        df_association.reset_index(drop=True, inplace=True)
        df_association.index = df_association.index + 1
        session_state.df_association = df_association

        # Mengkonversi daftar menjadi string
        frequent_itemsets = df_association.copy()
        frequent_itemsets["Rules"] = frequent_itemsets["Rules"].astype(str)

        # Menghilangkan duplikat berdasarkan nilai pada kolom 'Produk Rules'
        frequent_itemsets = frequent_itemsets.drop_duplicates(subset="Rules")
        # menghilankan kolom
        frequent_itemsets = frequent_itemsets.drop(
            columns=[
                "antecedent support",
                "consequent support",
                "support",
                "confidence",
                "lift",
            ]
        )

        # Mengembalikan nilai daftar dari string (opsional, tergantung pada kebutuhan)
        frequent_itemsets["Rules"] = frequent_itemsets["Rules"].apply(eval)
        frequent_itemsets = frequent_itemsets.reset_index(drop=True)

        # Mereset index dan mengatur index mulai dari 1
        frequent_itemsets.reset_index(drop=True, inplace=True)
        frequent_itemsets.index = frequent_itemsets.index + 1

        session_state.frequent_itemsets = frequent_itemsets

        # Mengkonversi daftar menjadi string
        df_association_unique = df_association.copy()
        df_association_unique["Rules"] = df_association_unique["Rules"].astype(str)

        # Menghilangkan duplikat berdasarkan nilai pada kolom 'Rules'
        df_association_unique = df_association_unique.drop_duplicates(subset="Rules")

        # menghilankan kolom
        df_association_unique = df_association_unique.drop(
            columns=["antecedent support", "consequent support", "support", "lift"]
        )

        # Mengembalikan nilai daftar dari string (opsional, tergantung pada kebutuhan)
        df_association_unique["Rules"] = df_association_unique["Rules"].apply(eval)
        df_association_unique = df_association_unique.reset_index(drop=True)

        # Menerapkan mapping langsung pada kolom 'Rules' mengganti kode barang dengan nama barang
        df_association_unique["Rules"] = df_association_unique["Rules"].apply(
            lambda rules: [kode_to_nama.get(kode, kode) for kode in rules]
        )

        # mengurutkan
        df_association_unique = df_association_unique.sort_values(
            by=["confidence"], ascending=False
        )

        # Mereset index dan mengatur index mulai dari 1
        df_association_unique.reset_index(drop=True, inplace=True)
        df_association_unique.index = df_association_unique.index + 1

        session_state.df_association_unique = df_association_unique

        # # # Pilah kombinasi terbanyak dan urutkan berdasarkan lift tertinggi untuk rekomendasi
        # # df_association_unique["Count Items"] = df_association_unique["Rules"].apply(len)

        # # # Memilih kombinasi dengan jumlah item terbesar dari setiap group berdasarkan 'Count Items'
        # # df_association_max_combination = df_association_unique.sort_values(
        # #     by=["Count Items", "lift"], ascending=[False, False]
        # # ).drop_duplicates(subset="Count Items", keep="first")

        # # # Reset index untuk dataframe yang sudah difilter
        # # df_association_max_combination.reset_index(drop=True, inplace=True)
        # # df_association_max_combination.index = df_association_max_combination.index + 1

        # # Simpan hasil ini di session_state
        # session_state.df_association_max_combination = df_association_max_combination

        return rules, frequent_itemsets

    def tampilProsesAturanAsosiasi():

        # tab1, tab2, tab3, tab4 = st.tabs(
        #     ["Data Transaksi", "Preparation", "Modelling", "Evaluation"]
        # )

        # MENAMPILKAN DATA TRANSAKSI
        # with tab1:
        df_transaksi = MiningData.getUploadTransaksi()
        df_transaksi.reset_index(drop=True, inplace=True)
        df_transaksi.index = df_transaksi.index + 1

        # df_transaksi = MiningData.pemilihanAtribut(df_transaksi)
        st.markdown("<h2>Data Transaksi</h2>", unsafe_allow_html=True)
        st.write(
            "Terdapat: ",
            df_transaksi.shape[0],
            "record dan",
            df_transaksi.shape[1],
            "atribut",
        )
        st.dataframe(df_transaksi)
        st.divider()

        # MENAMPILKAN PREPARATION
        # with tab2:
        st.markdown("<h2>Data Preparation</h2>", unsafe_allow_html=True)

        # MENAMPILKAN PREPARATION PILIH ATRIBUT
        st.markdown("<h3>Pemilihan Atribut</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p>Memilih atribut yang dibutuhkan yaitu No Invoice dan Kode</p>",
            unsafe_allow_html=True,
        )
        pilihAtribut = MiningData.pilihAtribut(df_transaksi)
        pilihAtribut = df_transaksi[["NO INVOICE", "KODE"]]
        st.dataframe(pilihAtribut)

        # MENAMPILKAN PREPARATION DATA CLEANING
        st.markdown("<h3>Data Cleaning</h3>", unsafe_allow_html=True)
        # st.write(pilih_atribut.isnull().sum())
        null_value_counts = pilihAtribut.isnull().sum()
        null_value_data = {"Kolom": [], "Jumlah Null": []}
        for col, count in null_value_counts.items():
            null_value_data["Kolom"].append(col.upper())
            null_value_data["Jumlah Null"].append(count)
        null_value_info_df = pd.DataFrame(null_value_data)

        st.write("Hasil informasi")
        st.dataframe(null_value_info_df)
        null_value_text = (
            "Diketahui, terdapat **{NO_INVOICE_NULL}** data yang bernilai kosong pada kolom NO INVOICE dan **{KODE_NULL}** data yang bernilai kosong pada kolom KODE."
        ).format(
            NO_INVOICE_NULL=null_value_counts["NO INVOICE"],
            KODE_NULL=null_value_counts["KODE"],
        )
        st.write(null_value_text)
        # Menampilkan data hasil cleaning data
        cleaningData = MiningData.cleaningData(pilihAtribut)
        st.markdown(
            "<p>Berikut adalah data setelah dibersihkan</p>",
            unsafe_allow_html=True,
        )

        st.dataframe(cleaningData)
        st.write(
            "Sehingga data yang digunakan saat ini memiliki ",
            cleaningData.shape[0],
            "baris data",
        )

        # MENAMPILKAN PREPARATION TRANSFORMASI DATA
        st.markdown("<h3 >Data Transform</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p>Mengabungkan nilai KODE menjadi satu list berdasarkan NO INVOICE</p>",
            unsafe_allow_html=True,
        )
        list_transaksi, transformData = MiningData.transformData(cleaningData)

        list_transaksi, transformData.reset_index(drop=True, inplace=True)
        list_transaksi, transformData.index = (
            list_transaksi,
            transformData.index + 1,
        )

        st.dataframe(list_transaksi)

        st.markdown(
            "<p>Data di transformasi kebentuk yang dibutuhkan untuk modelling</p>",
            unsafe_allow_html=True,
        )

        st.dataframe(transformData)
        st.divider()

        # MENAMPILKAN MODLING
        # MENAMPILKAN MODELING MIN SUPPORT
        # with tab3:
        st.markdown("<h2>Data Modeling</h2>", unsafe_allow_html=True)
        st.markdown("<h3>Menentukan Minimum Support</h3>", unsafe_allow_html=True)
        list_produk = MiningData.getListProduk()
        list_produk_show = list_produk[["KODE", "Support"]]
        st.dataframe(list_produk_show, use_container_width=True)
        st.markdown(
            "<p>Minimum support didapatkan dari rata-rata frekuensi barang pada seluruh transaksi",
            unsafe_allow_html=True,
        )
        get_frekuensi = list_produk["Support"].mean()
        st.write(
            "Rata-rata frekuensi: ",
            get_frekuensi,
            "dibulatkan keatas sehingga menjadi",
            round(get_frekuensi),
        )
        # get_len_transaction = len(transactions_list)

        # # Menghitung persentase minimum support
        # st.write("Jumlah Transaksi: ", get_len_transaction)
        # get_frekuensi = round(get_frekuensi)
        # st.write("Minimum support = {}/{}".format(get_frekuensi, get_len_transaction))
        # st.write("Minimum support = Mean frekuensi/jumlah transaksi")
        # min_support = get_frekuensi / get_len_transaction
        # min_support = round(get_frekuensi / len(transactions_list), 3)
        # # st.write("Minimum support = {}".format(min_support))

        # MENAMPILKAN MODELING MIN CONFIDENCE
        st.markdown("<h3>Menentukan Minimum Confidence</h3>", unsafe_allow_html=True)
        st.markdown(
            "<p>Nilai minimum confidence yang ditetapkan yaitu 70 persen berdasarkan referensi penelitian</p>",
            unsafe_allow_html=True,
        )
        min_confidence = 0.70
        st.write(min_confidence)

        #  MENAMPILKAN MODELING Frequent itemsets
        st.markdown("<h3>Frequent Itemsets</h3>", unsafe_allow_html=True)
        st.dataframe(session_state.frequent_itemsets, use_container_width=True)

        #  MENAMPILKAN MODELING Rules
        st.markdown("<h3>Rules yang terbentuk</h3>", unsafe_allow_html=True)
        st.write("terdapat: {} rules".format(session_state.rules.shape[0]))

        rules = session_state.rules.copy()
        rules = rules[
            [
                "antecedents",
                "consequents",
                "antecedent support",
                "consequent support",
                "support",
                "confidence",
                "lift"
            ]
        ]
        st.dataframe(rules, use_container_width=True)

        #  MENAMPILKAN EVALUASI RULES
        # with tab4:
        # st.markdown("<h2>Evaluasi</h2>", unsafe_allow_html=True)
        # st.markdown(
        #     "<h3>Menggabungkan antecedents dan consequents</h3>",
        #     unsafe_allow_html=True,
        # )
        # st.dataframe(session_state.df_association, use_container_width=True)

        st.markdown("<h2>Evaluasi</h2>", unsafe_allow_html=True)
        st.markdown(
            "<p>Berikut adalah evaluasi terhadap rule yang dihasilkan dari proses aturan asosiasi: pengembalian kode barang menjadi nama barang dan penghapusan dulikasi aturan</p>",
            unsafe_allow_html=True,
        )

        st.dataframe(session_state.df_association_unique, use_container_width=True)
        # st.divider
        # # st.dataframe(
        # #     session_state.df_association_max_combination, use_container_width=True
        # # )

    def unduhRekomendasi(df_rekomendasi):
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df_rekomendasi.to_excel(writer, sheet_name="rekomendasi", index=False)
        writer.close()  # Menutup objek writer
        output.seek(0)
        data_bundling_download = output.read()

        st.markdown("<h4>Unduh hasil rekomendasi</h4>", unsafe_allow_html=True)
        if st.download_button(
            label="Unduh",
            data=data_bundling_download,
            file_name="rekomendasi-produk.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download-button",
            use_container_width=True,
        ):
            st.success("Rekomendasi Berhasil di Unduh")

    def tampilHasilRekomendasi(df_dict):
        # versi 1
        # # Menggabungkan semua data dari df_dict menjadi satu DataFrame
        # df_rekomendasi_gabungan = pd.concat(df_dict.values(), ignore_index=True)

        # # Hapus kolom 'Kode Rules' jika tidak dibutuhkan
        # df_rekomendasi_gabungan = df_rekomendasi_gabungan.drop(columns=["Kode Rules"])

        # # Tambahkan kolom 'No' yang merepresentasikan index rekomendasi
        # df_rekomendasi_gabungan["No"] = [
        #     f"{i+1}" for i in range(len(df_rekomendasi_gabungan))
        # ]

        # # Set kolom 'No' sebagai index
        # df_rekomendasi_gabungan = df_rekomendasi_gabungan.set_index("No")

        # # Tampilkan hasil rekomendasi dalam satu tabel
        # st.dataframe(df_rekomendasi_gabungan[["Rekomendasi"]], use_container_width=True)
        # st.divider()

        # versi 2
        # Mengakses DataFrame untuk masing-masing Kode Rules menggunakan perulangan
        for kode_rules, rekomendasi in df_dict.items():
            st.write(f"Rekomendasi ke {kode_rules}")
            rekomendasi_show = rekomendasi.reset_index(drop=True)
            rekomendasi_show = rekomendasi_show.drop(columns=["Kode Rules"])

            # Tambahkan kolom 'no' dengan nilai dari index
            rekomendasi_show["No"] = [
                f"{kode_rules}" for i in range(len(rekomendasi_show))
            ]
            # rekomendasi_show = rekomendasi_show.set_index("No")

            # rekomendasi_show_table = rekomendasi_show[["Rekomendasi"]]

            # st.dataframe(rekomendasi_show_table, use_container_width=True)
            # st.divider()
            # rekomendasi_show["No"] = [kode_rules] * len(rekomendasi_show)

            # Konversi DataFrame ke HTML secara manual
            table_html = "<table>"
            table_html += "<tr><th>No</th><th>Rekomendasi</th></tr>"
            for i, row in rekomendasi_show.iterrows():
                rekomendasi_text = row["Rekomendasi"]
                table_html += (
                    f'<tr><td>{row["No"]}</td><td>{rekomendasi_text}</td></tr>'
                )
            table_html += "</table>"

            # Menampilkan tabel dengan HTML rendering
            st.markdown(table_html, unsafe_allow_html=True)
            st.divider()
