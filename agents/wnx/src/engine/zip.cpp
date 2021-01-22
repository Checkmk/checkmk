//
//
// Support for the Zip Files
//
//

#include "stdafx.h"

#include "zip.h"

#include <fmt/format.h>
#include <shellapi.h>

#include <filesystem>

#include "common/cfg_info.h"
#include "common/wtools.h"
#include "logger.h"

namespace cma::tools::zip {
// usually this pointer comes from Windows API
template <typename T>
struct ResourceReleaser {
    void operator()(T *r) noexcept {
        if (r) r->Release();
    }
};

// usage
#if (0)
ReleasedResource<FolderItems> fi(::WindowsApiToGetFi());
#endif
//
template <typename T>
using ReleasedResource = std::unique_ptr<T, ResourceReleaser<T>>;

static void InitVariant(VARIANT &var, BSTR bstr) {
    VariantInit(&var);
    var.vt = VT_BSTR;
    var.bstrVal = bstr;
}

static void InitVariantZipOptions(VARIANT &var) {
    VariantInit(&var);
    var.vt = VT_I4;
    var.lVal = FOF_NO_UI;
}

static void InitVariantFolderIetms(VARIANT &var, FolderItems *fi) {
    VariantInit(&var);
    var.vt = VT_DISPATCH;
    var.pdispVal = fi;
}

static HRESULT UnzipExec(Folder *to, FolderItems *fi) {
    VARIANT options;
    InitVariantZipOptions(options);

    VARIANT items;
    InitVariantFolderIetms(items, fi);

    return to->CopyHere(items, options);
}

static ReleasedResource<Folder> CreateFolder(IShellDispatch *dispatch,
                                             wtools::Bstr &bstr) {
    VARIANT variantDir;
    InitVariant(variantDir, bstr);
    Folder *folder = nullptr;
    auto hResult = dispatch->NameSpace(variantDir, &folder);

    if (!SUCCEEDED(hResult)) {
        XLOG::l("Error during NameSpace 1 /unzip/ {:#X}", hResult);
        return nullptr;
    }

    return ReleasedResource<Folder>{folder};
}

static bool CheckTheParameters(std::wstring_view file_src,
                               std::wstring_view dir_dest) {
    namespace fs = std::filesystem;
    fs::path file = file_src;
    fs::path dir = dir_dest;
    if (!fs::exists(file) || !fs::is_regular_file(file)) {
        XLOG::l("File '{}' is absent or not suitable", file);
        return false;
    }

    if (!fs::exists(dir) || !fs::is_directory(dir)) {
        XLOG::l("Dir '{}' is absent or not suitable to unzip", dir);
        return false;
    }

    return true;
}

static ReleasedResource<FolderItem> GetItem(FolderItems *fi, long i) {
    VARIANT var_index;
    VariantInit(&var_index);
    var_index.lVal = i;
    var_index.vt = VT_I4;

    FolderItem *item = nullptr;
    fi->Item(var_index, &item);
    ::VariantClear(&var_index);

    return ReleasedResource<FolderItem>{item};
}

static ReleasedResource<IShellDispatch> CreateShellDispatch() {
    IShellDispatch *dispatch = nullptr;
    auto hres = CoCreateInstance(CLSID_Shell, nullptr, CLSCTX_INPROC_SERVER,
                                 IID_IShellDispatch,
                                 reinterpret_cast<void **>(&dispatch));
    if (!SUCCEEDED(hres)) {
        XLOG::l("Error during Create Instance /unzip/ {:X}", hres);
        return nullptr;
    }

    return ReleasedResource<IShellDispatch>{dispatch};
}

static ReleasedResource<FolderItems> GetFolderItems(Folder *folder) {
    FolderItems *fi = nullptr;
    folder->Items(&fi);
    return ReleasedResource<FolderItems>{fi};
}

std::vector<std::wstring> List(std::wstring_view file_src) {
    namespace fs = std::filesystem;
    fs::path file = file_src;
    if (!fs::exists(file) || !fs::is_regular_file(file)) {
        XLOG::l("File '{}' is absent or not suitable", file);
        return {};
    }

    wtools::Bstr src(file_src);

    wtools::InitWindowsCom();

    auto dispatch = CreateShellDispatch();
    if (nullptr == dispatch) {
        XLOG::l("Error during Create Instance /unzip/");
        return {};
    }

    auto from_file = CreateFolder(dispatch.get(), src);
    if (from_file == nullptr) {
        XLOG::l("Error during NameSpace 1 /unzip/. The file is '{}'",
                wtools::ToUtf8(file_src));
        return {};
    }

    auto fi = GetFolderItems(from_file.get());
    if (fi == nullptr) {
        XLOG::l("Failed to get folder items /unzip/. The file is '{}'",
                wtools::ToUtf8(file_src));
        return {};
    }

    std::vector<std::wstring> vec;
    long count = 0;
    fi->get_Count(&count);
    for (int i = 0; i < count; i++) {
        auto item = GetItem(fi.get(), i);
        if (item == nullptr) continue;

        BSTR name;
        item->get_Name(&name);
        vec.emplace_back(name);
        ::SysFreeString(name);
    }

    return vec;
}

bool Extract(std::wstring_view file_src, std::wstring_view dir_dest) {
    if (!CheckTheParameters(file_src, dir_dest)) return false;

    wtools::Bstr src(file_src);
    wtools::Bstr dest(dir_dest);

    wtools::InitWindowsCom();

    auto dispatch = CreateShellDispatch();
    if (nullptr == dispatch) {
        XLOG::l("Error during Create Instance /unzip/");
        return false;
    }

    auto to_folder = CreateFolder(dispatch.get(), dest);  // out
    if (to_folder == nullptr) {
        XLOG::l("Error finding folder /unzip/");
        return false;
    }

    auto from_file = CreateFolder(dispatch.get(), src);  // in
    if (from_file == nullptr) {
        XLOG::l("Error finding from file /unzip/. The file is '{}'",
                wtools::ToUtf8(file_src));
        return false;
    }

    // files & folders
    auto file_items = GetFolderItems(from_file.get());
    if (file_items == nullptr) {
        XLOG::l("Failed to get folder items /unzip/. The file is '{}'",
                wtools::ToUtf8(file_src));
        return false;
    }

    auto hres = UnzipExec(to_folder.get(), file_items.get());

    if (hres != S_OK) {
        XLOG::l("Error during copy here /unzip/ {:#X}", hres);
        return false;
    }

    XLOG::l.i("SUCCESS /unzip/");
    return true;
}
}  // namespace cma::tools::zip
